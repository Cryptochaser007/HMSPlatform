"""Field validators for Indian healthcare and regulatory constraints."""

import re


def validate_phone_number(phone: str) -> bool:
    """Validate Indian 10-digit mobile number starting with 6, 7, 8, or 9."""
    clean = re.sub(r"\D", "", phone)
    if len(clean) == 12 and clean.startswith("91"):
        clean = clean[2:]
    return bool(re.match(r"^[6-9]\d{9}$", clean))


def validate_pincode(pincode: str) -> bool:
    """Validate 6-digit Indian postal PIN code (100000 to 999999)."""
    clean = str(pincode).strip()
    return bool(re.match(r"^[1-9]\d{5}$", clean))


def validate_gst_number(gst: str) -> bool:
    """Validate Indian 15-character GSTIN format."""
    pattern = r"^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
    return bool(re.match(pattern, gst.strip().upper()))


def validate_aadhaar_format(aadhaar: str) -> bool:
    """Validate standard 12-digit Aadhaar format."""
    clean = re.sub(r"\D", "", aadhaar)
    return len(clean) == 12


def validate_abha_format(abha_id: str) -> bool:
    """Validate standard ABHA number (XX-XXXX-XXXX-XXXX) or ABHA address."""
    if "@" in abha_id:
        # ABHA address e.g. name@abdm
        return bool(re.match(r"^[a-zA-Z0-9._-]+@[a-zA-Z0-9]+$", abha_id))
    clean = abha_id.replace("-", "")
    return bool(re.match(r"^\d{14}$", clean))


def validate_icd_code(code: str) -> bool:
    """Validate standard ICD-10 diagnostic code format (e.g. A00, I10.9)."""
    return bool(re.match(r"^[A-Z]\d{2}(\.\d{1,4})?$", code.strip().upper()))


def validate_blood_group(bg: str) -> bool:
    """Validate standard human blood group notation."""
    valid = {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"}
    return bg.strip().upper() in valid

