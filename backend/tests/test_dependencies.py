"""Unit tests for RBAC dependencies (app/core/dependencies.py).

Tests cover:
- get_current_user: token extraction and validation
- require_role: role-based access control checks
- require_admin, require_baker, require_customer shortcuts
- Error handling: 401 for missing/invalid tokens, 403 for unauthorized roles
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.dependencies import (
    get_current_user,
    require_role,
    require_admin,
    require_baker,
    require_customer,
)


# ============================================================
# get_current_user Tests
# ============================================================


class TestGetCurrentUser:
    """Tests for JWT token extraction and validation."""

    def test_missing_credentials_returns_401(self):
        """No Authorization header should raise 401."""
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials=None)
        assert exc_info.value.status_code == 401
        assert "Authentication required" in exc_info.value.detail

    def test_invalid_token_returns_401(self):
        """Invalid token that Supabase rejects should raise 401."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="invalid-token"
        )

        mock_supabase = MagicMock()
        mock_supabase.auth.get_user.side_effect = Exception("Invalid token")

        with patch(
            "app.core.dependencies._get_supabase_client",
            return_value=mock_supabase,
        ):
            with pytest.raises(HTTPException) as exc_info:
                get_current_user(credentials=credentials)
            assert exc_info.value.status_code == 401
            assert "Invalid or expired token" in exc_info.value.detail

    def test_expired_token_returns_401(self):
        """Expired token should raise 401."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="expired-token"
        )

        mock_supabase = MagicMock()
        mock_supabase.auth.get_user.side_effect = Exception("Token expired")

        with patch(
            "app.core.dependencies._get_supabase_client",
            return_value=mock_supabase,
        ):
            with pytest.raises(HTTPException) as exc_info:
                get_current_user(credentials=credentials)
            assert exc_info.value.status_code == 401

    def test_null_user_response_returns_401(self):
        """Supabase returning None user should raise 401."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="some-token"
        )

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.user = None
        mock_supabase.auth.get_user.return_value = mock_response

        with patch(
            "app.core.dependencies._get_supabase_client",
            return_value=mock_supabase,
        ):
            with pytest.raises(HTTPException) as exc_info:
                get_current_user(credentials=credentials)
            assert exc_info.value.status_code == 401

    def test_valid_token_returns_user_dict(self):
        """Valid token should return user dict with role from users table."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="valid-token"
        )

        mock_user = MagicMock()
        mock_user.id = "user-123"
        mock_user.email = "admin@example.com"

        mock_auth_response = MagicMock()
        mock_auth_response.user = mock_user

        mock_db_result = MagicMock()
        mock_db_result.data = {
            "id": "user-123",
            "email": "admin@example.com",
            "full_name": "Admin User",
            "phone": "0901234567",
            "role": "admin",
        }

        mock_supabase = MagicMock()
        mock_supabase.auth.get_user.return_value = mock_auth_response

        mock_admin_client = MagicMock()
        mock_admin_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = (
            mock_db_result
        )

        with patch(
            "app.core.dependencies._get_supabase_client",
            return_value=mock_supabase,
        ), patch(
            "app.core.dependencies.get_supabase_client",
            return_value=mock_admin_client,
        ):
            user = get_current_user(credentials=credentials)

        assert user["id"] == "user-123"
        assert user["email"] == "admin@example.com"
        assert user["full_name"] == "Admin User"
        assert user["phone"] == "0901234567"
        assert user["role"] == "admin"

    def test_user_not_in_users_table_defaults_to_customer(self):
        """User in auth but not in users table should default to customer role."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="valid-token"
        )

        mock_user = MagicMock()
        mock_user.id = "user-456"
        mock_user.email = "new@example.com"

        mock_auth_response = MagicMock()
        mock_auth_response.user = mock_user

        mock_db_result = MagicMock()
        mock_db_result.data = None  # User not found in users table

        mock_supabase = MagicMock()
        mock_supabase.auth.get_user.return_value = mock_auth_response

        mock_admin_client = MagicMock()
        mock_admin_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = (
            mock_db_result
        )

        with patch(
            "app.core.dependencies._get_supabase_client",
            return_value=mock_supabase,
        ), patch(
            "app.core.dependencies.get_supabase_client",
            return_value=mock_admin_client,
        ):
            user = get_current_user(credentials=credentials)

        assert user["id"] == "user-456"
        assert user["email"] == "new@example.com"
        assert user["role"] == "customer"


# ============================================================
# require_role Tests
# ============================================================


class TestRequireRole:
    """Tests for role-based access control dependency factory."""

    def test_matching_role_allows_access(self):
        """User with matching role should pass through."""
        checker = require_role(["admin"])
        user = {"id": "1", "email": "a@b.com", "full_name": "A", "phone": None, "role": "admin"}
        result = checker(current_user=user)
        assert result == user

    def test_non_matching_role_returns_403(self):
        """User without matching role should get 403."""
        checker = require_role(["admin"])
        user = {"id": "1", "email": "a@b.com", "full_name": "A", "phone": None, "role": "customer"}
        with pytest.raises(HTTPException) as exc_info:
            checker(current_user=user)
        assert exc_info.value.status_code == 403
        assert "Insufficient permissions" in exc_info.value.detail

    def test_multiple_roles_any_match(self):
        """User with any of the allowed roles should pass."""
        checker = require_role(["admin", "baker"])
        baker_user = {"id": "1", "email": "b@b.com", "full_name": "B", "phone": None, "role": "baker"}
        result = checker(current_user=baker_user)
        assert result == baker_user

    def test_multiple_roles_none_match(self):
        """User without any of the allowed roles should get 403."""
        checker = require_role(["admin", "baker"])
        customer = {"id": "1", "email": "c@b.com", "full_name": "C", "phone": None, "role": "customer"}
        with pytest.raises(HTTPException) as exc_info:
            checker(current_user=customer)
        assert exc_info.value.status_code == 403

    def test_missing_role_field_returns_403(self):
        """User dict without role field should get 403."""
        checker = require_role(["admin"])
        user = {"id": "1", "email": "a@b.com", "full_name": "A", "phone": None}
        with pytest.raises(HTTPException) as exc_info:
            checker(current_user=user)
        assert exc_info.value.status_code == 403


# ============================================================
# Shortcut Dependency Tests
# ============================================================


class TestRoleShortcuts:
    """Tests for require_admin, require_baker, require_customer shortcuts."""

    def test_require_admin_allows_admin(self):
        user = {"id": "1", "email": "a@b.com", "full_name": "A", "phone": None, "role": "admin"}
        result = require_admin(current_user=user)
        assert result["role"] == "admin"

    def test_require_admin_denies_customer(self):
        user = {"id": "1", "email": "a@b.com", "full_name": "A", "phone": None, "role": "customer"}
        with pytest.raises(HTTPException) as exc_info:
            require_admin(current_user=user)
        assert exc_info.value.status_code == 403

    def test_require_admin_denies_baker(self):
        user = {"id": "1", "email": "a@b.com", "full_name": "A", "phone": None, "role": "baker"}
        with pytest.raises(HTTPException) as exc_info:
            require_admin(current_user=user)
        assert exc_info.value.status_code == 403

    def test_require_baker_allows_baker(self):
        user = {"id": "1", "email": "a@b.com", "full_name": "A", "phone": None, "role": "baker"}
        result = require_baker(current_user=user)
        assert result["role"] == "baker"

    def test_require_baker_denies_customer(self):
        user = {"id": "1", "email": "a@b.com", "full_name": "A", "phone": None, "role": "customer"}
        with pytest.raises(HTTPException) as exc_info:
            require_baker(current_user=user)
        assert exc_info.value.status_code == 403

    def test_require_customer_allows_customer(self):
        user = {"id": "1", "email": "a@b.com", "full_name": "A", "phone": None, "role": "customer"}
        result = require_customer(current_user=user)
        assert result["role"] == "customer"

    def test_require_customer_denies_admin(self):
        user = {"id": "1", "email": "a@b.com", "full_name": "A", "phone": None, "role": "admin"}
        with pytest.raises(HTTPException) as exc_info:
            require_customer(current_user=user)
        assert exc_info.value.status_code == 403
