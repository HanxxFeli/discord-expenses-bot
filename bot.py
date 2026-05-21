import os
from datetime import datetime, timezone

import discord
from dotenv import load_dotenv

from ai_classifier import classify_expense
from parser import parse_expense_message
from sheets import append_expense

load_dotenv()

# Intents are Discord's permission system for bots.
# You must request exactly what your bot needs — nothing more.
intents = discord.Intents.default()
intents.message_content = True  # Required to read message text

bot = discord.Client(intents=intents)

# The Discord channel where expense messages are posted.
# Only messages in this channel will be processed.
EXPENSE_CHANNEL_ID = int(os.getenv("EXPENSE_CHANNEL_ID", "0"))


@bot.event
async def on_ready() -> None:
    """Called once when the bot successfully connects to Discord."""
    print(f"[Bot] Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"[Bot] Watching channel ID: {EXPENSE_CHANNEL_ID}")


@bot.event
async def on_message(message: discord.Message) -> None:
    """
    Called every time ANY message is sent in any channel the bot can see.
    
    We filter down to:
    1. The correct channel
    2. Not sent by a bot (prevents infinite loops)
    3. Matches our expense format
    """
    
    # Ignore messages from bots (including ourselves)
    if message.author.bot:
        return
    
    # Ignore messages outside the designated expense channel
    if message.channel.id != EXPENSE_CHANNEL_ID:
        return
    
    content = message.content.strip()
    
    # Try to parse the message
    raw = parse_expense_message(content, str(message.author))
    
    if raw is None:
        # Not an expense message — could be a question or comment.
        # Only reply if the message looks like it was TRYING to be an expense.
        if ";" in content:
            parts = content.split(";")
            # Check if the error is specifically a bad person name
            from parser import get_person_error
            person_error = get_person_error(parts[0]) if len(parts) >= 1 else None
            
            if person_error:
                await message.reply(person_error)
            else:
                await message.reply(
                    "⚠️ Couldn't parse that. Format: `Person; description; amount`\n"
                    "Valid persons: `Hans`, `Hyemin`, `Both`\n"
                    "Example: `Hans; mcdonalds; 12.54`"
                )
        return
    
    # Show a loading reaction so the user knows it's being processed
    await message.add_reaction("⏳")
    
    try:
        # Step 1: AI Classification
        # We pass the ISO timestamp so it's consistent between classification and logging
        timestamp = raw.timestamp.isoformat()
        
        expense = classify_expense(
            person=raw.person,
            description=raw.description,
            amount=raw.amount,
            timestamp=timestamp,
            discord_user=raw.discord_user,
            raw_message=raw.raw_message,
            user_note=raw.user_note,
        )
        
        # Step 2: Log to Google Sheets
        row_number = append_expense(expense)
        
        # Step 3: Confirm to the user
        # Remove loading reaction, add success reaction
        await message.remove_reaction("⏳", bot.user)
        await message.add_reaction("✅")
        
        # Send a rich embed as confirmation — easier to read than plain text
        embed = discord.Embed(
            title="💸 Expense Logged",
            color=discord.Color.green(),
        )
        embed.add_field(name="Person", value=expense.person, inline=True)
        embed.add_field(name="Merchant", value=expense.merchant, inline=True)
        embed.add_field(name="Amount", value=f"${expense.amount:.2f}", inline=True)
        embed.add_field(name="Category", value=expense.category, inline=True)
        embed.add_field(name="Subcategory", value=expense.subcategory or "—", inline=True)
        embed.add_field(name="Row", value=f"#{row_number}", inline=True)
        if expense.notes:
            embed.add_field(name="Notes", value=expense.notes, inline=False)
        embed.set_footer(text=f"Logged at {raw.timestamp.strftime('%b %d, %Y %H:%M')}")
        
        await message.reply(embed=embed)
    
    except Exception as e:
        # Something went wrong — tell the user and print the full error for debugging
        await message.remove_reaction("⏳", bot.user)
        await message.add_reaction("❌")
        await message.reply(f"❌ Failed to log expense: `{e}`")
        print(f"[Error] {e}")
        raise  # Re-raise so the full traceback appears in your terminal


# This is the entry point — everything above is just definitions.
# bot.run() starts the event loop and keeps the script alive indefinitely.
bot.run(os.getenv("DISCORD_TOKEN"))