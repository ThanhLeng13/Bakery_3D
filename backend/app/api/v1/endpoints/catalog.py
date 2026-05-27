"""Catalog API endpoints.

Endpoints:
- GET /api/v1/products - List products (paginated, filtered by category)
- GET /api/v1/products/{id} - Product detail
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.core.dependencies import get_supabase_client
from app.schemas.catalog import ProductDetailResponse, ProductListResponse
from app.services.catalog_service import (
    CatalogService,
    CatalogServiceError,
    ProductNotFoundError,
)

router = APIRouter()


def _get_catalog_service() -> CatalogService:
    """Create CatalogService with Supabase client."""
    client = get_supabase_client(use_service_role=False)
    return CatalogService(client)


@router.get("", response_model=ProductListResponse)
async def list_products(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(
        default=20, ge=1, le=100, description="Items per page (default 20, max 100)"
    ),
    category: Optional[str] = Query(
        default=None, description="Filter by product category"
    ),
):
    """
    List active products with pagination and optional category filter.

    Products are sorted by newest first (created_at DESC).
    Only active products are returned.
    Returns empty list with pagination metadata when no products match.
    """
    catalog_service = _get_catalog_service()

    try:
        result = await catalog_service.list_products(
            page=page,
            page_size=page_size,
            category=category,
        )
        return result
    except CatalogServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/{product_id}", response_model=ProductDetailResponse)
async def get_product_detail(product_id: str):
    """
    Get full product detail by ID.

    Returns product with all details including images, sizes, flavors,
    average rating, and review count.
    Returns 404 if product not found or inactive.
    """
    catalog_service = _get_catalog_service()

    try:
        result = await catalog_service.get_product_detail(product_id)
        return result
    except ProductNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )
    except CatalogServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
