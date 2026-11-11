"""Utility helper functions for IDs, numbers, formatting, and cryptography."""

from datetime import date, datetime
from decimal import Decimal
import random
import re
import string


def generate_uhid() -> str:
    """Generate Unique Hospital Identification number. Format: UHID-YYYYMMDD-XXXXX."""
    today_str = datetime.now().strftime("%Y%m%d")
    random_suffix = "".join(random.choices(string.digits, k=5))
    return f"UHID-{today_str}-{random_suffix}"


def generate_bill_number() -> str:
    """Generate unique Bill Number. Format: BILL-YYYYMMDD-XXXXX."""
    today_str = datetime.now().strftime("%Y%m%d")
    random_suffix = "".join(random.choices(string.digits, k=5))
    return f"BILL-{today_str}-{random_suffix}"


def generate_receipt_number() -> str:
    """Generate payment Receipt Number. Format: RCP-YYYYMMDD-XXXXX."""
    today_str = datetime.now().strftime("%Y%m%d")
    random_suffix = "".join(random.choices(string.digits, k=5))
    return f"RCP-{today_str}-{random_suffix}"


def generate_sample_id() -> str:
    """Generate Lab Sample Barcode ID. Format: SAM-YYYYMMDD-XXXXX."""
    today_str = datetime.now().strftime("%Y%m%d")
    random_suffix = "".join(random.choices(string.digits, k=5))
    return f"SAM-{today_str}-{random_suffix}"


def generate_accession_number() -> str:
    """Generate Radiology PACS Accession Number. Format: ACC-YYYYMMDD-XXXX."""
    today_str = datetime.now().strftime("%Y%m%d")
    random_suffix = "".join(random.choices(string.digits, k=4))
    return f"ACC-{today_str}-{random_suffix}"


def generate_incident_number() -> str:
    """Generate NABH Incident Report Number. Format: INC-YYYYMMDD-XXXX."""
    today_str = datetime.now().strftime("%Y%m%d")
    random_suffix = "".join(random.choices(string.digits, k=4))
    return f"INC-{today_str}-{random_suffix}"


def format_indian_currency(amount: Decimal) -> str:
    """Format decimal amount as Indian Rupee string (e.g. ₹1,23,456.78)."""
    amount_str = f"{amount:.2f}"
    parts = amount_str.split(".")
    integer_part = parts[0]
    decimal_part = parts[1]

    if len(integer_part) <= 3:
        formatted = integer_part
    else:
        last_three = integer_part[-3:]
        remaining = integer_part[:-3]
        # Group remaining by 2 digits from right to left
        grouped = []
        while len(remaining) > 2:
            grouped.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            grouped.insert(0, remaining)
        formatted = ",".join(grouped) + "," + last_three

    return f"₹{formatted}.{decimal_part}"


def calculate_age(dob: date) -> dict:
    """Calculate age in years, months, days from date of birth."""
    today = date.today()
    years = today.year - dob.year
    months = today.month - dob.month
    days = today.day - dob.day

    if days < 0:
        months -= 1
        days += 30
    if months < 0:
        years -= 1
        months += 12

    return {"years": years, "months": months, "days": days}


# Verhoeff algorithm multiplication table & permutation table for Aadhaar validation
_VERHOEFF_D = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
    (2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
    (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
    (4, 0, 1, 2, 3, 9, 5, 6, 7, 8),
    (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
    (6, 5, 9, 8, 7, 1, 0, 4, 3, 2),
    (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
    (8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
    (9, 8, 7, 6, 5, 4, 3, 2, 1, 0),
)
_VERHOEFF_P = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
    (5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
    (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
    (9, 4, 5, 3, 1, 2, 6, 8, 7, 0),
    (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
    (2, 7, 9, 3, 8, 0, 6, 4, 1, 5),
    (7, 0, 4, 6, 9, 1, 3, 2, 5, 8),
)


def validate_aadhaar(number: str) -> bool:
    """Validate 12-digit Aadhaar number using Verhoeff checksum algorithm."""
    clean = re.sub(r"\D", "", number)
    if len(clean) != 12:
        return False
    # Verhoeff check
    c = 0
    for i, item in enumerate(reversed(clean)):
        c = _VERHOEFF_D[c][_VERHOEFF_P[i % 8][int(item)]]
    return c == 0


def validate_abha_id(abha_id: str) -> bool:
    """Validate 14-digit ABHA ID formatted as XX-XXXX-XXXX-XXXX or 14 digits."""
    clean = abha_id.replace("-", "")
    return bool(re.match(r"^\d{14}$", clean))


def mask_aadhaar(number: str) -> str:
    """Mask Aadhaar showing only last 4 digits (e.g. XXXX-XXXX-1234)."""
    clean = re.sub(r"\D", "", number)
    if len(clean) == 12:
        return f"XXXX-XXXX-{clean[-4:]}"
    return "XXXX-XXXX-XXXX"


def mask_phone(phone: str) -> str:
    """Mask phone showing only last 4 digits (e.g. XXXXXX1234)."""
    clean = re.sub(r"\D", "", phone)
    if len(clean) >= 4:
        return "X" * (len(clean) - 4) + clean[-4:]
    return phone


def sanitize_input(text: str) -> str:
    """Strip dangerous characters to prevent injection attacks."""
    if not text:
        return ""
    # Strip script tags, null bytes, HTML markup
    cleaned = re.sub(r"<[^>]*>", "", text)
    cleaned = cleaned.replace("\x00", "")
    return cleaned.strip()


def parse_indian_phone(phone: str) -> str:
    """Normalize phone number to standard E.164 +91XXXXXXXXXX."""
    clean = re.sub(r"\D", "", phone)
    if clean.startswith("91") and len(clean) == 12:
        return f"+{clean}"
    if len(clean) == 10:
        return f"+91{clean}"
    return phone

