"""
Input validation helpers.

Each function returns (is_valid: bool, cleaned_value_or_error: str).
"""

import re

_PHONE_RE = re.compile(r"^\+?[1-9]\d{7,14}$")
_HASH_RE = re.compile(r"^[a-fA-F0-9]{32}$")


def validate_api_id(text: str) -> tuple[bool, str]:
    text = text.strip()
    if not text.isdigit():
        return False, "API_ID must be a number. Please send only digits (e.g. 12345678)."
    if len(text) < 5 or len(text) > 10:
        return False, "That doesn't look like a valid API_ID. Please double-check it on my.telegram.org."
    return True, text


def validate_api_hash(text: str) -> tuple[bool, str]:
    text = text.strip()
    if not _HASH_RE.match(text):
        return False, "API_HASH must be a 32-character hexadecimal string. Please check my.telegram.org and try again."
    return True, text.lower()


def validate_phone(text: str) -> tuple[bool, str]:
    text = text.strip().replace(" ", "").replace("-", "")
    if not text.startswith("+"):
        text = "+" + text
    if not _PHONE_RE.match(text):
        return False, "Please send a valid phone number in international format, e.g. +919876543210."
    return True, text


def validate_otp(text: str) -> tuple[bool, str]:
    digits = re.sub(r"\D", "", text.strip())
    if not digits or len(digits) < 4 or len(digits) > 7:
        return False, "That doesn't look like a valid login code. Please send only the digits Telegram sent you."
    return True, digits


def validate_password(text: str) -> tuple[bool, str]:
    text = text.strip()
    if not text:
        return False, "Password cannot be empty. Please send your Two-Step Verification password."
    if len(text) > 256:
        return False, "That password looks too long to be valid. Please double-check and try again."
    return True, text
