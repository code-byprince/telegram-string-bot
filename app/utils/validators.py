"""
Input validators
"""

import re


def validate_api_id(api_id: str) -> bool:
    """Validate API_ID format"""
    try:
        value = int(api_id)
        return 1 <= value <= 2147483647  # Telegram API ID range
    except (ValueError, TypeError):
        return False


def validate_api_hash(api_hash: str) -> bool:
    """Validate API_HASH format"""
    if not api_hash:
        return False
    
    # API_HASH is typically a 32-character alphanumeric string
    return bool(re.match(r'^[a-zA-Z0-9]{32}$', api_hash))


def validate_phone(phone: str) -> bool:
    """Validate phone number format"""
    if not phone:
        return False
    
    # Remove whitespace and special characters
    cleaned = re.sub(r'[\s\-()\+]', '', phone)
    
    # Check if it starts with + or digits
    if not phone.startswith('+'):
        return False
    
    # Remove leading +
    number = phone[1:]
    
    # Check if it contains only digits
    if not number.isdigit():
        return False
    
    # Check length (minimum 8 digits, maximum 15 digits)
    if not (8 <= len(number) <= 15):
        return False
    
    return True


def validate_otp(otp: str) -> bool:
    """Validate OTP format"""
    if not otp:
        return False
    
    # OTP should be 5 or 6 digits
    return bool(re.match(r'^\d{5,6}$', otp))


def validate_password(password: str) -> bool:
    """Validate 2FA password"""
    if not password:
        return False
    
    # Password should be at least 1 character (basic validation)
    return len(password) >= 1
