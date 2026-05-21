import json
import os
from dataclasses import dataclass

from google import genai
from dotenv import load_dotenv

load_dotenv()

# The new SDK uses a Client object instead of module-level configuration.
# This is cleaner — the API key is tied to the client, not a global.
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# gemini-2.0-flash is the current free, fast model in the new SDK
MODEL = "gemini-2.5-flash"


@dataclass
class ClassifiedExpense:
    """A fully enriched expense after AI classification."""
    person: str
    description: str
    merchant: str          # Cleaned merchant name (e.g. "McDonald's" not "mcdonalds")
    amount: float
    category: str          # e.g. "Food & Dining", "Transport", "Groceries"
    subcategory: str       # e.g. "Fast Food", "Coffee", "Fuel"
    notes: str             # Any useful context the AI inferred
    timestamp: str         # ISO format string for Sheets
    discord_user: str
    raw_message: str


# The categories we want Gemini to choose from.
# Keeping a fixed list ensures your Sheets graphs have consistent groupings.
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
    timestamp: str,
    discord_user: str,
    raw_message: str,
) -> ClassifiedExpense:
    """
    Use Gemini to classify an expense and return enriched data.
    
    We use a structured JSON prompt so the response is machine-readable.
    If AI fails, we fall back to safe defaults — the expense still gets logged.
    """
    
    prompt = f"""You are an expense classification assistant. Classify the following expense and respond ONLY with a valid JSON object — no explanation, no markdown, no backticks.

Expense details:
- Person: {person}
- Description: "{description}"
- Amount: ${amount:.2f}

Classify into one of these exact categories: {", ".join(CATEGORIES)}

Respond with this exact JSON structure:
{{
  "merchant": "cleaned merchant name with proper capitalization",
  "category": "one of the categories listed above",
  "subcategory": "a more specific label (e.g. Fast Food, Taxi, Supermarket)",
  "notes": "any useful context (e.g. 'Likely lunch expense', 'Recurring bill'). Empty string if nothing to add."
}}"""

    try:
        # New SDK call: client.models.generate_content()
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
        )
        
        result = json.loads(response.text.strip())
        
        return ClassifiedExpense(
            person=person,
            description=description,
            merchant=result.get("merchant", description),
            amount=amount,
            category=result.get("category", "Other"),
            subcategory=result.get("subcategory", ""),
            notes=result.get("notes", ""),
            timestamp=timestamp,
            discord_user=discord_user,
            raw_message=raw_message,
        )
    
    except Exception as e:
        # If AI fails for any reason, log it and return a safe default.
        # The expense STILL gets recorded — we never lose data.
        print(f"[AI] Classification failed: {e}. Using fallback.")
        return ClassifiedExpense(
            person=person,
            description=description,
            merchant=description.title(),
            amount=amount,
            category="Other",
            subcategory="Unclassified",
            notes="AI classification failed",
            timestamp=timestamp,
            discord_user=discord_user,
            raw_message=raw_message,
        )