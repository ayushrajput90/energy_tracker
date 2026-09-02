import re
from datetime import datetime

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

def validate_email(email: str) -> bool:
    if not email or not isinstance(email, str):
        return False
    return bool(EMAIL_REGEX.match(email.strip()))

def validate_password(password: str) -> tuple[bool, str]:
    if not password or len(password) < 6:
        return False, "Password must be at least 6 characters long."
    return True, ""

def validate_date(date_str: str) -> tuple[bool, str]:
    if not date_str:
        return False, "Date is required."
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True, ""
    except ValueError:
        return False, "Invalid date format. Use YYYY-MM-DD."

def validate_numeric(val, field_name: str, allow_negative: bool = False) -> tuple[bool, float, str]:
    try:
        num = float(val)
        if not allow_negative and num < 0:
            return False, 0.0, f"{field_name} cannot be negative."
        return True, num, ""
    except (ValueError, TypeError):
        return False, 0.0, f"{field_name} must be a valid number."
