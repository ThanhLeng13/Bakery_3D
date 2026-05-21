"""Unit tests for catalog service and endpoints."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.services.catalog_service import (
    CatalogService,
    CatalogServiceError,
    ProductNotFoundError,
)


# ============================================================
# Test Fixtures
# ============================================================


def make_product(
    product_id=None,
    name="Bánh kem socola",
    description="Bánh kem socola ngon tuyệt",
    category="bánh âu",
    base_price=250000,
    is_active=True,
    sizes=None,
    flavors=None,
    created_at="2024-01-15T10:00:00+00:00",
    updated_at="2024-01-15T10:00:00+00:00",
):
    """Create a product dict for testing."""
    return {
        "id": product_id or str(uuid4()),
        "name": name,
        "description": description,
        "category": category,
        "base_price": base_price,
        "is_active": is_active,
        "sizes": sizes or [{"name": "16cm", "price": 250000}],
        "flavors": flavors or [{"name": "Socola", "price": 0}],
        "created_at": created_at,
        "updated_at": updated_at,
    }


class MockQueryBuilder:
    """Mock Supabase query builder that supports chaining."""

    def __init__(self, data=None, count=None):
        self._data = data
        self._count = count

    def select(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def range(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def maybe_single(self):
        return self

    def single(self):
        return self

    def execute(self):
        result = MagicMock()
        result.data = self._data
        result.count = self._count
        return result


# ============================================================
# CatalogService.list_products Tests
# ============================================================


class TestListProducts:
    """Tests for CatalogService.list_products."""

    @pytest.fixture
    def mock_supabase(self):
        """Create a mock Supabase client."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_list_products_returns_paginated_results(self, mock_supabase):
        """Should return products with pagination metadata."""
        product = make_product()

        # Mock count query
        count_builder = MockQueryBuilder(data=[{"id": product["id"]}], count=1)
        # Mock data query
        data_builder = MockQueryBuilder(data=[product])
        # Mock images query
        images_builder = MockQueryBuilder(data=[{"url": "https://example.com/img.jpg"}])
        # Mock reviews query
        reviews_builder = MockQueryBuilder(data=[{"rating": 4}, {"rating": 5}])

        call_count = {"value": 0}

        def mock_table(table_name):
            call_count["value"] += 1
            if table_name == "products":
                # First call is count, second is data
                if call_count["value"] == 1:
                    return count_builder
                return data_builder
            elif table_name == "product_images":
                return images_builder
            elif table_name == "reviews":
                return reviews_builder
            return MockQueryBuilder()

        mock_supabase.table = mock_table

        service = CatalogService(mock_supabase)
        result = await service.list_products(page=1, page_size=20)

        assert "products" in result
        assert "pagination" in result
        assert len(result["products"]) == 1
        assert result["products"][0]["name"] == "Bánh kem socola"
        assert result["products"][0]["image_url"] == "https://example.com/img.jpg"
        assert result["products"][0]["average_rating"] == 4.5
        assert result["products"][0]["review_count"] == 2
        assert result["pagination"]["page"] == 1
        assert result["pagination"]["page_size"] == 20
        assert result["pagination"]["total_items"] == 1
        assert result["pagination"]["total_pages"] == 1
        assert result["pagination"]["has_next"] is False
        assert result["pagination"]["has_previous"] is False

    @pytest.mark.asyncio
    async def test_list_products_empty_catalog(self, mock_supabase):
        """Should return empty list with zero pagination when no products exist."""
        count_builder = MockQueryBuilder(data=[], count=0)
        data_builder = MockQueryBuilder(data=[])

        call_count = {"value": 0}

        def mock_table(table_name):
            call_count["value"] += 1
            if table_name == "products":
                if call_count["value"] == 1:
                    return count_builder
                return data_builder
            return MockQueryBuilder()

        mock_supabase.table = mock_table

        service = CatalogService(mock_supabase)
        result = await service.list_products()

        assert result["products"] == []
        assert result["pagination"]["total_items"] == 0
        assert result["pagination"]["total_pages"] == 0
        assert result["pagination"]["has_next"] is False
        assert result["pagination"]["has_previous"] is False

    @pytest.mark.asyncio
    async def test_list_products_truncates_description(self, mock_supabase):
        """Should truncate description to 100 characters in list view."""
        long_desc = "A" * 150
        product = make_product(description=long_desc)

        count_builder = MockQueryBuilder(data=[{"id": product["id"]}], count=1)
        data_builder = MockQueryBuilder(data=[product])
        images_builder = MockQueryBuilder(data=[])
        reviews_builder = MockQueryBuilder(data=[])

        call_count = {"value": 0}

        def mock_table(table_name):
            call_count["value"] += 1
            if table_name == "products":
                if call_count["value"] == 1:
                    return count_builder
                return data_builder
            elif table_name == "product_images":
                return images_builder
            elif table_name == "reviews":
                return reviews_builder
            return MockQueryBuilder()

        mock_supabase.table = mock_table

        service = CatalogService(mock_supabase)
        result = await service.list_products()

        assert len(result["products"][0]["description"]) == 100

    @pytest.mark.asyncio
    async def test_list_products_no_image_returns_none(self, mock_supabase):
        """Should return None for image_url when product has no images."""
        product = make_product()

        count_builder = MockQueryBuilder(data=[{"id": product["id"]}], count=1)
        data_builder = MockQueryBuilder(data=[product])
        images_builder = MockQueryBuilder(data=[])
        reviews_builder = MockQueryBuilder(data=[])

        call_count = {"value": 0}

        def mock_table(table_name):
            call_count["value"] += 1
            if table_name == "products":
                if call_count["value"] == 1:
                    return count_builder
                return data_builder
            elif table_name == "product_images":
                return images_builder
            elif table_name == "reviews":
                return reviews_builder
            return MockQueryBuilder()

        mock_supabase.table = mock_table

        service = CatalogService(mock_supabase)
        result = await service.list_products()

        assert result["products"][0]["image_url"] is None

    @pytest.mark.asyncio
    async def test_list_products_no_reviews_returns_null_rating(self, mock_supabase):
        """Should return None for average_rating when product has no reviews."""
        product = make_product()

        count_builder = MockQueryBuilder(data=[{"id": product["id"]}], count=1)
        data_builder = MockQueryBuilder(data=[product])
        images_builder = MockQueryBuilder(data=[])
        reviews_builder = MockQueryBuilder(data=[])

        call_count = {"value": 0}

        def mock_table(table_name):
            call_count["value"] += 1
            if table_name == "products":
                if call_count["value"] == 1:
                    return count_builder
                return data_builder
            elif table_name == "product_images":
                return images_builder
            elif table_name == "reviews":
                return reviews_builder
            return MockQueryBuilder()

        mock_supabase.table = mock_table

        service = CatalogService(mock_supabase)
        result = await service.list_products()

        assert result["products"][0]["average_rating"] is None
        assert result["products"][0]["review_count"] == 0


# ============================================================
# CatalogService.get_product_detail Tests
# ============================================================


class TestGetProductDetail:
    """Tests for CatalogService.get_product_detail."""

    @pytest.fixture
    def mock_supabase(self):
        """Create a mock Supabase client."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_get_product_detail_success(self, mock_supabase):
        """Should return full product detail with images and reviews."""
        product_id = str(uuid4())
        product = make_product(product_id=product_id)

        product_builder = MockQueryBuilder(data=product)
        images_builder = MockQueryBuilder(
            data=[
                {"id": str(uuid4()), "url": "https://example.com/1.jpg", "sort_order": 0},
                {"id": str(uuid4()), "url": "https://example.com/2.jpg", "sort_order": 1},
            ]
        )
        reviews_builder = MockQueryBuilder(data=[{"rating": 3}, {"rating": 4}, {"rating": 5}])

        call_count = {"value": 0}

        def mock_table(table_name):
            call_count["value"] += 1
            if table_name == "products":
                return product_builder
            elif table_name == "product_images":
                return images_builder
            elif table_name == "reviews":
                return reviews_builder
            return MockQueryBuilder()

        mock_supabase.table = mock_table

        service = CatalogService(mock_supabase)
        result = await service.get_product_detail(product_id)

        assert result["id"] == product_id
        assert result["name"] == "Bánh kem socola"
        assert result["description"] == "Bánh kem socola ngon tuyệt"
        assert result["category"] == "bánh âu"
        assert result["base_price"] == 250000
        assert len(result["sizes"]) == 1
        assert len(result["flavors"]) == 1
        assert len(result["images"]) == 2
        assert result["average_rating"] == 4.0
        assert result["review_count"] == 3

    @pytest.mark.asyncio
    async def test_get_product_detail_not_found(self, mock_supabase):
        """Should raise ProductNotFoundError when product doesn't exist."""
        product_builder = MockQueryBuilder(data=None)

        def mock_table(table_name):
            return product_builder

        mock_supabase.table = mock_table

        service = CatalogService(mock_supabase)

        with pytest.raises(ProductNotFoundError):
            await service.get_product_detail(str(uuid4()))

    @pytest.mark.asyncio
    async def test_get_product_detail_inactive_not_found(self, mock_supabase):
        """Should raise ProductNotFoundError for inactive products."""
        # The query filters by is_active=True, so inactive products return None
        product_builder = MockQueryBuilder(data=None)

        def mock_table(table_name):
            return product_builder

        mock_supabase.table = mock_table

        service = CatalogService(mock_supabase)

        with pytest.raises(ProductNotFoundError):
            await service.get_product_detail(str(uuid4()))

    @pytest.mark.asyncio
    async def test_get_product_detail_no_images(self, mock_supabase):
        """Should return empty images list when product has no images."""
        product_id = str(uuid4())
        product = make_product(product_id=product_id)

        product_builder = MockQueryBuilder(data=product)
        images_builder = MockQueryBuilder(data=[])
        reviews_builder = MockQueryBuilder(data=[])

        call_count = {"value": 0}

        def mock_table(table_name):
            call_count["value"] += 1
            if table_name == "products":
                return product_builder
            elif table_name == "product_images":
                return images_builder
            elif table_name == "reviews":
                return reviews_builder
            return MockQueryBuilder()

        mock_supabase.table = mock_table

        service = CatalogService(mock_supabase)
        result = await service.get_product_detail(product_id)

        assert result["images"] == []

    @pytest.mark.asyncio
    async def test_get_product_detail_null_sizes_flavors(self, mock_supabase):
        """Should return empty lists when sizes/flavors are null in DB."""
        product_id = str(uuid4())
        product = make_product(product_id=product_id, sizes=None, flavors=None)
        # Simulate DB returning None for JSONB fields
        product["sizes"] = None
        product["flavors"] = None

        product_builder = MockQueryBuilder(data=product)
        images_builder = MockQueryBuilder(data=[])
        reviews_builder = MockQueryBuilder(data=[])

        call_count = {"value": 0}

        def mock_table(table_name):
            call_count["value"] += 1
            if table_name == "products":
                return product_builder
            elif table_name == "product_images":
                return images_builder
            elif table_name == "reviews":
                return reviews_builder
            return MockQueryBuilder()

        mock_supabase.table = mock_table

        service = CatalogService(mock_supabase)
        result = await service.get_product_detail(product_id)

        assert result["sizes"] == []
        assert result["flavors"] == []


# ============================================================
# ProductNotFoundError Tests
# ============================================================


class TestProductNotFoundError:
    """Tests for ProductNotFoundError exception."""

    def test_error_has_404_status(self):
        """Should have status_code 404."""
        error = ProductNotFoundError("some-id")
        assert error.status_code == 404

    def test_error_message_contains_product_id(self):
        """Should include product ID in error message."""
        error = ProductNotFoundError("abc-123")
        assert "abc-123" in error.message


# ============================================================
# Schema Tests
# ============================================================


class TestCatalogSchemas:
    """Tests for catalog Pydantic schemas."""

    def test_product_list_response_empty(self):
        """Should accept empty product list."""
        from app.schemas.catalog import PaginationMeta, ProductListResponse

        response = ProductListResponse(
            products=[],
            pagination=PaginationMeta(
                page=1,
                page_size=20,
                total_items=0,
                total_pages=0,
                has_next=False,
                has_previous=False,
            ),
        )
        assert response.products == []
        assert response.pagination.total_items == 0

    def test_product_detail_response(self):
        """Should accept full product detail."""
        from datetime import datetime

        from app.schemas.catalog import ProductDetailResponse, ProductImage

        response = ProductDetailResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            name="Test Cake",
            description="A test cake",
            category="bánh âu",
            base_price=250000,
            sizes=[{"name": "16cm", "price": 250000}],
            flavors=[{"name": "Socola", "price": 0}],
            is_active=True,
            images=[
                ProductImage(
                    id="550e8400-e29b-41d4-a716-446655440001",
                    url="https://example.com/img.jpg",
                    sort_order=0,
                )
            ],
            average_rating=4.5,
            review_count=10,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert response.name == "Test Cake"
        assert len(response.images) == 1
        assert response.average_rating == 4.5
