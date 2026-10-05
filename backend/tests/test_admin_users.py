"""Tests for the admin user-management endpoints.

Regression note: list_users() used to select users.branch_id, a column that has
never existed in the schema (no migration adds it), so the endpoint raised a
PostgREST 42703 error and returned 500 on every call - the Nhân sự screen could
never load. Unit tests cannot see a schema mismatch, so this file covers the
behaviour and the select list is verified against the live database separately.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.admin_users import list_users, update_user_role


def _mock_db(rows):
    """Build a mock supabase client whose orders().select() chain returns rows."""
    db = MagicMock()
    db.table.return_value.select.return_value.order.return_value.execute.return_value = MagicMock(
        data=rows
    )
    db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
        data=rows[0] if rows else None
    )
    db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
        data=rows
    )
    return db


class TestListUsers:
    """GET /api/v1/admin/users"""

    def test_returns_users_and_total(self):
        rows = [
            {"id": "1", "email": "a@example.com", "full_name": "A", "role": "customer"},
            {"id": "2", "email": "b@example.com", "full_name": "B", "role": "baker"},
        ]
        with patch(
            "app.api.v1.endpoints.admin_users.get_supabase_client", return_value=_mock_db(rows)
        ):
            result = list_users(admin={"id": "admin-1", "role": "admin"})

        assert result["total"] == 2
        assert [u["email"] for u in result["users"]] == ["a@example.com", "b@example.com"]

    def test_does_not_select_a_branch_id_column(self):
        """Guard against re-adding a column the users table does not have."""
        db = _mock_db([{"id": "1", "email": "a@example.com", "role": "customer"}])
        with patch(
            "app.api.v1.endpoints.admin_users.get_supabase_client", return_value=db
        ):
            list_users(admin={"id": "admin-1", "role": "admin"})

        selected = db.table.return_value.select.call_args[0][0]
        assert "branch_id" not in selected
        for column in selected.split(","):
            assert column.strip() in {"id", "email", "full_name", "phone", "role"}

    def test_query_failure_returns_500_with_safe_message(self):
        db = MagicMock()
        db.table.return_value.select.return_value.order.return_value.execute.side_effect = RuntimeError(
            "column users.branch_id does not exist"
        )
        with patch(
            "app.api.v1.endpoints.admin_users.get_supabase_client", return_value=db
        ):
            with pytest.raises(HTTPException) as exc_info:
                list_users(admin={"id": "admin-1", "role": "admin"})

        assert exc_info.value.status_code == 500
        # The raw database error must not leak to the client.
        assert "branch_id" not in exc_info.value.detail


class TestUpdateUserRole:
    """PATCH /api/v1/admin/users/{user_id}/role"""

    def test_cannot_demote_yourself(self):
        with pytest.raises(HTTPException) as exc_info:
            update_user_role(
                "admin-1", type("Body", (), {"role": "customer"})(), admin={"id": "admin-1", "role": "admin"}
            )
        assert exc_info.value.status_code == 400

    def test_cannot_change_another_admin(self):
        db = _mock_db([{"id": "2", "role": "admin"}])
        with patch(
            "app.api.v1.endpoints.admin_users.get_supabase_client", return_value=db
        ):
            with pytest.raises(HTTPException) as exc_info:
                update_user_role(
                    "2", type("Body", (), {"role": "baker"})(), admin={"id": "admin-1", "role": "admin"}
                )
        assert exc_info.value.status_code == 403

    def test_unknown_user_returns_404(self):
        db = _mock_db([])
        with patch(
            "app.api.v1.endpoints.admin_users.get_supabase_client", return_value=db
        ):
            with pytest.raises(HTTPException) as exc_info:
                update_user_role(
                    "missing",
                    type("Body", (), {"role": "baker"})(),
                    admin={"id": "admin-1", "role": "admin"},
                )
        assert exc_info.value.status_code == 404
