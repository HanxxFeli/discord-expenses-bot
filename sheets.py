import os
from typing import Any

import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

# Google APIs require "scopes" — you declare exactly what permissions you need.
# These two scopes cover reading and writing Sheets and Drive (needed for file access).
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# The header row — this defines your columns.
# Order matters: this is the exact order rows will be appended in.
HEADERS = [
    "Date",           # 2025-01-15
    "Time",           # 14:32
    "Person",         # Hans
    "Merchant",       # McDonald's
    "Description",    # mcdonalds
    "Amount",         # 12.54
    "Category",       # Food & Dining
    "Subcategory",    # Fast Food
    "Notes",          # Likely lunch expense
    "Discord User",   # hans#1234
    "Raw Message",    # Hans; mcdonalds; 12.54
]


def get_sheet() -> gspread.Worksheet:
    """
    Authenticate and return the first worksheet of the target spreadsheet.
    
    We create a new client each call to keep this module stateless.
    For a high-volume app you'd cache this, but for expense tracking it's fine.
    """
    creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(os.getenv("SPREADSHEET_ID"))
    return spreadsheet.sheet1


def ensure_headers(sheet: gspread.Worksheet) -> None:
    """
    Check if row 1 has our headers. If not, insert them.
    
    This is idempotent — safe to call every time the bot starts.
    """
    first_row = sheet.row_values(1)
    if first_row != HEADERS:
        # Insert headers at row 1, shifting everything else down
        sheet.insert_row(HEADERS, index=1)
        print("[Sheets] Headers inserted.")


def append_expense(expense: Any) -> int:
    """
    Append a ClassifiedExpense as a new row. Returns the row number.
    
    We accept `Any` type here to avoid a circular import between sheets.py
    and ai_classifier.py. In a larger app you'd put the dataclass in a
    separate models.py file.
    """
    sheet = get_sheet()
    ensure_headers(sheet)
    
    # Parse the ISO timestamp back into date/time components for separate columns.
    # Separate columns make it much easier to build charts filtered by date or hour.
    from datetime import datetime
    dt = datetime.fromisoformat(expense.timestamp)
    date_str = dt.strftime("%Y-%m-%d")   # e.g. 2025-01-15
    time_str = dt.strftime("%H:%M")      # e.g. 14:32
    
    row = [
        date_str,
        time_str,
        expense.person,
        expense.merchant,
        expense.description,
        expense.amount,        # Keep as number — Sheets will treat it as numeric
        expense.category,
        expense.subcategory,
        expense.notes,
        expense.discord_user,
        expense.raw_message,
    ]
    
    sheet.append_row(row, value_input_option="USER_ENTERED")
    # USER_ENTERED means Sheets will parse the amount as a number, not text
    
    # Return the row number for confirmation messages
    return len(sheet.get_all_values())