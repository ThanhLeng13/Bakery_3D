"""Security regression tests: internal error details must not leak to clients.

Rationale
---------
`ProductServiceError` and `AuthServiceError` messages are serialised straight
into the HTTP response body by their respective endpoint handlers:

    admin_products._handle_product_error -> {"detail": e.message}

Before this fix, several `except Exception as e:` blocks embedded the raw
driver/Postgres exception text in that message (``f"...: {str(e)}"``), so an
internal failure surfaced things like table names, column names and SQL
fragments to any admin client. These tests lock the safe behaviour in place:
the exception message stays generic, while the detail is still written to the
server log for operators.
"""

import logging
from unittest.mock import MagicMock

import pytest

from app.services.product_service import (
    ProductService,
    ProductServiceError,
    ProductValidationError,
)


# Text that a real Postgres/driver error would contain. If any of this reaches
# the raised exception message, the leak has regressed.
SENSITIVE_DRIVER_ERROR = (
    'relation "public.products_secret" does not exist '
    "LINE 1: select * from products_secret where owner_id = 'abc'"
)


class TestProductServiceDoesNotLeakInternals:
    """Every broad `except Exception` in ProductService must stay generic."""

    def setup_method(self):
        self.mock_supabase = MagicMock()
        self.service = ProductService(self.mock_supabase)
        self.valid_data = {
            "name": "Bánh Ngọt",
            "description": "Ngon",
            "category": "bánh ngọt",
            "base_price": 50000,
            "sizes": [{"name": "Nhỏ", "price": 0}],
            "flavors": ["Dâu"],
        }

    def test_create_product_hides_driver_error(self):
        self.mock_supabase.table().insert().execute.side_effect = Exception(
            SENSITIVE_DRIVER_ERROR
        )

        with pytest.raises(ProductServiceError) as exc:
            self.service.create_product(self.valid_data)

        assert str(exc.value) == "Failed to create product"
        assert "products_secret" not in str(exc.value)
        assert "LINE 1" not in str(exc.value)

    def test_update_product_hides_driver_error(self):
        self.mock_supabase.table().select().eq().maybe_single().execute.return_value = (
            MagicMock(data={"id": "prod-1"})
        )
        self.mock_supabase.table().update().eq().execute.side_effect = Exception(
            SENSITIVE_DRIVER_ERROR
        )

        with pytest.raises(ProductServiceError) as exc:
            self.service.update_product("prod-1", {"name": "X"})

        assert str(exc.value) == "Failed to update product"
        assert "products_secret" not in str(exc.value)

    def test_toggle_status_hides_driver_error(self):
        self.mock_supabase.table().select().eq().maybe_single().execute.return_value = (
            MagicMock(data={"id": "prod-1"})
        )
        self.mock_supabase.table().update().eq().execute.side_effect = Exception(
            SENSITIVE_DRIVER_ERROR
        )

        with pytest.raises(ProductServiceError) as exc:
            self.service.toggle_status("prod-1", True)

        assert str(exc.value) == "Failed to toggle status"
        assert "products_secret" not in str(exc.value)

    def test_fetch_product_hides_driver_error(self):
        # `_get_product_or_raise` treats None/empty data as 404, so raise the
        # driver error from the query itself to reach the broad handler.
        self.mock_supabase.table().select().eq().maybe_single().execute.side_effect = (
            Exception(SENSITIVE_DRIVER_ERROR)
        )

        with pytest.raises(ProductServiceError) as exc:
            self.service._get_product_or_raise("prod-1")

        assert str(exc.value) == "Failed to fetch product"
        assert "products_secret" not in str(exc.value)


class TestProductServiceLogsInternals:
    """The detail must still reach operators via the server log."""

    def test_create_product_logs_exception(self, caplog):
        mock_supabase = MagicMock()
        service = ProductService(mock_supabase)
        mock_supabase.table().insert().execute.side_effect = Exception(
            SENSITIVE_DRIVER_ERROR
        )

        with caplog.at_level(logging.ERROR):
            with pytest.raises(ProductServiceError):
                service.create_product(
                    {
                        "name": "Bánh Ngọt",
                        "description": "Ngon",
                        "category": "bánh ngọt",
                        "base_price": 50000,
                        "sizes": [{"name": "Nhỏ", "price": 0}],
                        "flavors": ["Dâu"],
                    }
                )

        # The full driver text is preserved server-side for debugging.
        assert "products_secret" in caplog.text


class TestImageValidationMessage:
    """Corrupt uploads must return an actionable but non-internal message."""

    def test_corrupt_image_message_is_generic(self):
        mock_supabase = MagicMock()
        service = ProductService(mock_supabase)

        with pytest.raises(ProductValidationError) as exc:
            # Not a valid image payload, so Pillow raises internally.
            service._process_image(b"definitely-not-an-image", "image/png")

        # The endpoint serialises `errors`, so that is the text a client sees.
        assert exc.value.errors[0]["field"] == "image"
        assert exc.value.errors[0]["message"] == "Invalid or corrupt image file"
        serialised = str(exc.value.errors)
        assert "PIL" not in serialised
        assert "Traceback" not in serialised
        assert "0x" not in serialised  # no leaked object reprs
