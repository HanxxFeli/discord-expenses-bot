from dataclasses import dataclass
from datetime import datetime

# The only valid values for the "person" field.
# Normalised to title-case so "hans", "HANS", "Hans" all work.
VALID_PERSONS = {"Hans", "Hyemin", "Both"}


@dataclass
class RawExpense:
    """Represents the raw parsed data from a Discord message before AI enrichment."""
    person: str
    description: str
    amount: float
    timestamp: datetime
    raw_message: str
    discord_user: str


def parse_expense_message(message_content: str, author_name: str) -> RawExpense | None:
    """
    Parse a Discord message into a RawExpense.
    
    Expected format: "Person; description; amount"
    Valid persons: Hans, Hyemin, Both
    Example: "Hans; mcdonalds; 12.54"
    
    Returns None if the message doesn't match the expected format.
    """
    parts = [p.strip() for p in message_content.split(";")]
    
    if len(parts) != 3:
        return None
    
    person_raw, description, amount_str = parts
    
    # Normalise capitalisation so "hans" and "HANS" both work
    person = person_raw.title()
    
    if person not in VALID_PERSONS:
        # Return a special sentinel so bot.py can give a helpful error message
        # rather than silently ignoring the message
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
    )


def is_expense_attempt(message_content: str) -> bool:
    """Returns True if the message looks like it was trying to be an expense."""
    return ";" in message_content


def get_person_error(person_raw: str) -> str | None:
    """
    If the person field is invalid, return a helpful error string.
    Returns None if the person is valid.
    """
    person = person_raw.strip().title()
    if person not in VALID_PERSONS:
        return f"⚠️ Unknown person `{person_raw}`. Use: `Hans`, `Hyemin`, or `Both`."
    return None