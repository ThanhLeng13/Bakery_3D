"""Unit tests for authentication service components.

Tests cover:
- Password validation (security.py)
- Phone validation (security.py)
- Rate limiter logic (rate_limiter.py)
- Registration schema validation (schemas/auth.py)
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from app.core.rate_limiter import LoginRateLimiter
from app.core.security import validate_password, validate_phone, validate_email_length
from app.schemas.auth import RegisterRequest


# ============================================================
# Password Validation Tests
# ============================================================


class TestPasswordValidation:
    """Tests for password complexity validation."""

    def test_valid_password(self):
        errors = validate_password("Abcdef1!")
        assert errors == []

    def test_valid_password_min_length(self):
        errors = validate_password("Abcdef1x")
        assert errors == []

    def test_valid_password_max_length(self):
        password = "A" + "a" * 125 + "1x"
        errors = validate_password(password)
        assert errors == []

    def test_too_short(self):
        errors = validate_password("Ab1defg")
        assert any("at least 8" in e for e in errors)

    def test_too_long(self):
        password = "A" + "a" * 127 + "1"
        errors = validate_password(password)
        assert any("at most 128" in e for e in errors)

    def test_missing_uppercase(self):
        errors = validate_password("abcdefg1")
        assert any("uppercase" in e for e in errors)

    def test_missing_lowercase(self):
        errors = validate_password("ABCDEFG1")
        assert any("lowercase" in e for e in errors)

    def test_missing_digit(self):
        errors = validate_password("Abcdefgh")
        assert any("digit" in e for e in errors)

    def test_multiple_errors(self):
        errors = validate_password("abc")
        assert len(errors) >= 2  # too short + missing uppercase + missing digit


# ============================================================
# Phone Validation Tests
# ============================================================


class TestPhoneValidation:
    """Tests for Vietnamese phone format validation."""

    def test_valid_phone(self):
        assert validate_phone("0901234567") is True

    def test_valid_phone_all_digits(self):
        assert validate_phone("1234567890") is True

    def test_too_short(self):
        assert validate_phone("090123456") is False

    def test_too_long(self):
        assert validate_phone("09012345678") is False

    def test_contains_letters(self):
        assert validate_phone("090123456a") is False

    def test_contains_special_chars(self):
        assert validate_phone("090-123456") is False

    def test_empty_string(self):
        assert validate_phone("") is False


# ============================================================
# Email Length Validation Tests
# ============================================================


class TestEmailLengthValidation:
    """Tests for email length constraint."""

    def test_valid_email_length(self):
        assert validate_email_length("user@example.com") is True

    def test_max_length_email(self):
        email = "a" * 240 + "@example.com"  # 252 chars
        assert validate_email_length(email) is True

    def test_too_long_email(self):
        email = "a" * 250 + "@example.com"  # 262 chars
        assert validate_email_length(email) is False


# ============================================================
# Rate Limiter Tests
# ============================================================


class TestLoginRateLimiter:
    """Tests for in-memory login rate limiting."""

    def setup_method(self):
        """Create a fresh rate limiter for each test."""
        self.limiter = LoginRateLimiter()

    def test_not_locked_initially(self):
        assert self.limiter.is_locked("test@example.com") is False

    def test_not_locked_after_few_attempts(self):
        for _ in range(4):
            self.limiter.record_failed_attempt("test@example.com")
        assert self.limiter.is_locked("test@example.com") is False

    def test_locked_after_5_attempts(self):
        for _ in range(5):
            self.limiter.record_failed_attempt("test@example.com")
        assert self.limiter.is_locked("test@example.com") is True

    def test_record_returns_true_on_lockout(self):
        for _ in range(4):
            result = self.limiter.record_failed_attempt("test@example.com")
            assert result is False
        result = self.limiter.record_failed_attempt("test@example.com")
        assert result is True

    def test_different_emails_independent(self):
        for _ in range(5):
            self.limiter.record_failed_attempt("user1@example.com")
        assert self.limiter.is_locked("user1@example.com") is True
        assert self.limiter.is_locked("user2@example.com") is False

    def test_reset_clears_attempts(self):
        for _ in range(4):
            self.limiter.record_failed_attempt("test@example.com")
        self.limiter.reset("test@example.com")
        assert self.limiter.get_attempts_count("test@example.com") == 0
        assert self.limiter.is_locked("test@example.com") is False

    def test_lockout_remaining_seconds(self):
        for _ in range(5):
            self.limiter.record_failed_attempt("test@example.com")
        remaining = self.limiter.get_lockout_remaining("test@example.com")
        # Should be close to 900 seconds (15 minutes)
        assert 890 <= remaining <= 900

    def test_attempts_count(self):
        self.limiter.record_failed_attempt("test@example.com")
        self.limiter.record_failed_attempt("test@example.com")
        assert self.limiter.get_attempts_count("test@example.com") == 2

    def test_old_attempts_expire(self):
        """Attempts older than 15 minutes should be cleaned up."""
        email = "test@example.com"
        # Manually insert old timestamps
        from app.core.rate_limiter import LoginAttemptRecord

        old_time = time.time() - (16 * 60)  # 16 minutes ago
        self.limiter._records[email] = LoginAttemptRecord(
            attempts=[old_time, old_time, old_time, old_time]
        )
        # After cleanup, these should not count
        assert self.limiter.get_attempts_count(email) == 0


# ============================================================
# Registration Schema Validation Tests
# ============================================================


class TestRegisterRequestSchema:
    """Tests for registration request Pydantic validation."""

    def test_valid_registration(self):
        req = RegisterRequest(
            email="user@example.com",
            password="Password1",
            full_name="Nguyen Van A",
            phone="0901234567",
        )
        assert req.email == "user@example.com"
        assert req.full_name == "Nguyen Van A"

    def test_invalid_email(self):
        with pytest.raises(Exception):
            RegisterRequest(
                email="not-an-email",
                password="Password1",
                full_name="Test User",
                phone="0901234567",
            )

    def test_password_too_short(self):
        with pytest.raises(Exception):
            RegisterRequest(
                email="user@example.com",
                password="Pass1",
                full_name="Test User",
                phone="0901234567",
            )

    def test_password_no_uppercase(self):
        with pytest.raises(Exception):
            RegisterRequest(
                email="user@example.com",
                password="password1",
                full_name="Test User",
                phone="0901234567",
            )

    def test_password_no_lowercase(self):
        with pytest.raises(Exception):
            RegisterRequest(
                email="user@example.com",
                password="PASSWORD1",
                full_name="Test User",
                phone="0901234567",
            )

    def test_password_no_digit(self):
        with pytest.raises(Exception):
            RegisterRequest(
                email="user@example.com",
                password="Passwordx",
                full_name="Test User",
                phone="0901234567",
            )

    def test_phone_invalid_format(self):
        with pytest.raises(Exception):
            RegisterRequest(
                email="user@example.com",
                password="Password1",
                full_name="Test User",
                phone="12345",
            )

    def test_full_name_too_long(self):
        with pytest.raises(Exception):
            RegisterRequest(
                email="user@example.com",
                password="Password1",
                full_name="A" * 101,
                phone="0901234567",
            )
