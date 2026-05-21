"""JWT utilities and password validation helpers."""

import re
from typing import Optional

from jose import JWTError, jwt

from app.core.config import settings


def validate_password(password: str) -> list[str]:
    """
    Validate password complexity requirements.

    Returns a list of error messages. Empty list means valid.
    Requirements:
    - 8-128 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    """
    errors = []

    if len(password) < 8:
        errors.append("Password must be at least 8 characters")
    if len(password) > 128:
        errors.append("Password must be at most 128 characters")
    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")
    if not re.search(r"\d", password):
        errors.append("Password must contain at least one digit")

    return errors


def validate_phone(phone: str) -> bool:
    """Validate Vietnamese phone format (exactly 10 digits)."""
    return bool(re.match(r"^\d{10}$", phone))


def validate_email_length(email: str) -> bool:
    """Validate email length constraint (max 254 chars)."""
    return len(email) <= 254


def decode_jwt_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT token.

    Returns the payload dict if valid, None if invalid/expired.
    Note: In production, Supabase issues the JWTs. This utility
    is for local validation when needed.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError:
        return None


def get_token_remaining_seconds(payload: dict) -> int:
    """
    Get remaining seconds before token expiration.

    Returns 0 if token is already expired or has no exp claim.
    """
    import time

    exp = payload.get("exp")
    if exp is None:
        return 0
    remaining = int(exp - time.time())
    return max(0, remaining)


def should_refresh_token(payload: dict) -> bool:
    """
    Check if token should be auto-refreshed.

    Returns True if less than 5 minutes (300 seconds) remain.
    """
    remaining = get_token_remaining_seconds(payload)
    return remaining < 300 and remaining > 0
