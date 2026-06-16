"""Tests for product admin service."""

from unittest.mock import MagicMock, patch
import pytest

from app.services.product_service import (
    ProductNotFoundError,
    ProductService,
    ProductServiceError,
    ProductValidationError,
)


class TestProductServiceCreate:
    def setup_method(self):
        self.mock_supabase = MagicMock()
        self.product_service = ProductService(self.mock_supabase)
        self.valid_data = {
            "name": "Bánh Ngọt",
            "description": "Ngon",
            "category": "bánh ngọt",
            "base_price": 50000,
            "sizes": [{"name": "Nhỏ", "price": 0}],
            "flavors": ["Dâu"],
        }
    def test_create_product_success(self):
        self.mock_supabase.table().insert().execute.return_value = MagicMock(
            data=[{"id": "prod-1", "name": "Bánh Ngọt"}]
        )
        
        result = self.product_service.create_product(self.valid_data)
        assert result["id"] == "prod-1"
        assert result["images"] == []
        
        args = self.mock_supabase.table().insert.call_args[0][0]
        assert args["name"] == "Bánh Ngọt"
        assert args["is_active"] is True
    def test_create_product_duplicate_name(self):
        self.mock_supabase.table().insert().execute.side_effect = Exception("duplicate key value violates unique constraint")
        
        with pytest.raises(ProductValidationError) as exc:
            self.product_service.create_product(self.valid_data)
        assert exc.value.status_code == 422
        assert exc.value.errors[0]["field"] == "name"
    def test_create_product_general_error(self):
        self.mock_supabase.table().insert().execute.side_effect = Exception("DB connection lost")
        
        with pytest.raises(ProductServiceError):
            self.product_service.create_product(self.valid_data)


class TestProductServiceUpdate:
    def setup_method(self):
        self.mock_supabase = MagicMock()
        self.product_service = ProductService(self.mock_supabase)
    def test_update_product_success(self):
        # Mock product exists check
        self.mock_supabase.table().select().eq().maybe_single().execute.return_value = MagicMock(
            data={"id": "prod-1"}
        )
        
        # Mock update
        self.mock_supabase.table().update().eq().execute.return_value = MagicMock(
            data=[{"id": "prod-1"}]
        )
        
        # Mock fetching images
        self.mock_supabase.table().select().eq().order().execute.return_value = MagicMock(
            data=[]
        )
        
        result = self.product_service.update_product("prod-1", {"name": "New Name"})
        assert result["id"] == "prod-1"
        assert result["images"] == []
        
        args = self.mock_supabase.table().update.call_args[0][0]
        assert args["name"] == "New Name"
    def test_update_product_not_found(self):
        self.mock_supabase.table().select().eq().maybe_single().execute.return_value = MagicMock(data=None)
        
        with pytest.raises(ProductNotFoundError):
            self.product_service.update_product("prod-1", {"name": "New Name"})


class TestProductServiceToggleStatus:
    def setup_method(self):
        self.mock_supabase = MagicMock()
        self.product_service = ProductService(self.mock_supabase)
    def test_toggle_status_success(self):
        # Mock product exists check
        self.mock_supabase.table().select().eq().maybe_single().execute.return_value = MagicMock(
            data={"id": "prod-1"}
        )
        
        # Mock update
        self.mock_supabase.table().update().eq().execute.return_value = MagicMock(
            data=[{"id": "prod-1", "is_active": False}]
        )
        
        # Mock images
        self.mock_supabase.table().select().eq().order().execute.return_value = MagicMock(data=[])
        
        result = self.product_service.toggle_status("prod-1", False)
        assert result["id"] == "prod-1"
        
        args = self.mock_supabase.table().update.call_args[0][0]
        assert args["is_active"] is False


class TestProductServiceUploadImage:
    def setup_method(self):
        self.mock_supabase = MagicMock()
        self.product_service = ProductService(self.mock_supabase)
    def test_upload_image_invalid_type(self):
        self.mock_supabase.table().select().eq().maybe_single().execute.return_value = MagicMock(
            data={"id": "prod-1"}
        )
        
        with pytest.raises(ProductValidationError) as exc:
            self.product_service.upload_image("prod-1", b"fake", "application/pdf", "file.pdf")
        assert "Unsupported format" in exc.value.errors[0]["message"]
    def test_upload_image_too_large(self):
        self.mock_supabase.table().select().eq().maybe_single().execute.return_value = MagicMock(
            data={"id": "prod-1"}
        )
        
        # 6MB file
        large_file = b"0" * (6 * 1024 * 1024)
        
        with pytest.raises(ProductValidationError) as exc:
            self.product_service.upload_image("prod-1", large_file, "image/jpeg", "file.jpg")
        assert "5MB" in exc.value.errors[0]["message"]
