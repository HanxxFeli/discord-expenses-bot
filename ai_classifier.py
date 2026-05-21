import json
import os
from dataclasses import dataclass

from google import genai
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-2.5-flash"


@dataclass
class ClassifiedExpense:
    person: str
    description: str
    merchant: str
    amount: float
    card: str
    category: str
    subcategory: str
    notes: str
    timestamp: str
    discord_user: str
    raw_message: str


CATEGORIES = [
    "Food & Dining",
    "Groceries",
    "Transport",
    "Entertainment",
    "Shopping",
    "Health & Medical",
    "Utilities & Bills",
    "Travel",
    "Coffee & Drinks",
    "Other",
]


def classify_expense(
    person: str,
    description: str,
    amount: float,
    card: str,
    timestamp: str,
    discord_user: str,
    raw_message: str,
    user_note: str = "",
) -> ClassifiedExpense:
    prompt = f"""You are an expense classification assistant. Classify the following expense and respond ONLY with a valid JSON object — no explanation, no markdown, no backticks.

Expense details:
- Person: {person}
- Description: "{description}"
- Amount: ${amount:.2f}
- Card used: {card}
- User note: "{user_note}"

Classify into one of these exact categories: {", ".join(CATEGORIES)}

Respond with this exact JSON structure:
{{
  "merchant": "cleaned merchant name with proper capitalization",
  "category": "one of the categories listed above",
  "subcategory": "a more specific label (e.g. Fast Food, Taxi, Supermarket)",
  "notes": "any useful context. Empty string if nothing to add."
}}"""

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
        )

        result = json.loads(response.text.strip())

        ai_notes = result.get("notes", "")
        combined_notes = f"{user_note} | {ai_notes}".strip(" |") if user_note else ai_notes

        return ClassifiedExpense(
            person=person,
            description=description,
            merchant=result.get("merchant", description),
            amount=amount,
            card=card,
            category=result.get("category", "Other"),
            subcategory=result.get("subcategory", ""),
            notes=combined_notes,
            timestamp=timestamp,
            discord_user=discord_user,
            raw_message=raw_message,
        )

    except Exception as e:
        print(f"[AI] Classification failed: {e}. Using fallback.")
        return ClassifiedExpense(
            person=person,
            description=description,
            merchant=description.title(),
            amount=amount,
            card=card,
            category="Other",
            subcategory="Unclassified",
            notes=user_note or "AI classification failed",
            timestamp=timestamp,
            discord_user=discord_user,
            raw_message=raw_message,
        )