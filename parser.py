from dataclasses import dataclass
from datetime import datetime

VALID_PERSONS = {"Hans", "Hyemin", "Both"}

VALID_CARDS = {
    "rbc": "Hans RBC Credit",
    "cibc": "Hans CIBC Credit",
    "scotia": "Hyemin Scotiabank Debit",
}


@dataclass
class RawExpense:
    person: str
    description: str
    amount: float
    timestamp: datetime
    raw_message: str
    discord_user: str
    card: str
    user_note: str = ""


def parse_expense_message(message_content: str, author_name: str) -> RawExpense | None:
    """
    Format: Person; description; amount; card; note(optional)
    Example: Hans; mcdonalds; 12.54; rbc; lunch with Hyemin
    """
    parts = [p.strip() for p in message_content.split(";")]

    # Need at least 4 parts (note is optional)
    if len(parts) not in (4, 5):
        return None

    person_raw = parts[0]
    description = parts[1]
    amount_str = parts[2]
    card_raw = parts[3].lower()
    user_note = parts[4] if len(parts) == 5 else ""

    person = person_raw.title()
    if person not in VALID_PERSONS:
        return None

    if card_raw not in VALID_CARDS:
        return None

    try:
        amount = float(amount_str.replace("$", "").replace(",", ""))
    except ValueError:
        return None

    if amount <= 0 or amount > 100_000:
        return None

    return RawExpense(
        person=person,
        description=description,
        amount=amount,
        timestamp=datetime.now(),
        raw_message=message_content,
        discord_user=author_name,
        card=VALID_CARDS[card_raw],
        user_note=user_note,
    )


def is_expense_attempt(message_content: str) -> bool:
    return ";" in message_content


def get_parse_error(message_content: str) -> str | None:
    """Return a helpful error string if the message is malformed."""
    parts = [p.strip() for p in message_content.split(";")]

    if len(parts) < 4:
        return (
            "⚠️ Missing fields. Format: `Person; description; amount; card`\n"
            "Example: `Hans; mcdonalds; 12.54; rbc`"
        )

    person = parts[0].strip().title()
    if person not in VALID_PERSONS:
        return f"⚠️ Unknown person `{parts[0]}`. Use: `Hans`, `Hyemin`, or `Both`."

    card = parts[3].strip().lower()
    if card not in VALID_CARDS:
        return f"⚠️ Unknown card `{parts[3]}`. Use: `rbc`, `cibc`, or `scotia`."

    return None