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
    user_note: str = ""  # default empty so old code doesn't break


def parse_expense_message(message_content: str, author_name: str) -> RawExpense | None:
    parts = [p.strip() for p in message_content.split(";")]
    
    # Accept 3 parts (no note) or 4 parts (with note)
    if len(parts) not in (3, 4):
        return None
    
    person_raw = parts[0]
    description = parts[1]
    amount_str = parts[2]
    user_note = parts[3] if len(parts) == 4 else ""  # optional
    
    person = person_raw.title()
    if person not in VALID_PERSONS:
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
        user_note=user_note,  # new field
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