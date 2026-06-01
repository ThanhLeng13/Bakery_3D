"""Pydantic schemas for catalog endpoints."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ProductImage(BaseModel):
    """Product image schema."""

    id: UUID
    url: str
    sort_order: int = 0


class ProductListItem(BaseModel):
    """Product item in catalog list view."""

    id: UUID
    name: str
    description: Optional[str] = None
    category: str
    base_price: int
    product_type: str = "sweet"
    image_url: Optional[str] = None
    average_rating: Optional[float] = None
    review_count: int = 0
    created_at: datetime


class ProductDetailResponse(BaseModel):
    """Full product detail response."""

    id: UUID
    name: str
    description: Optional[str] = None
    category: str
    base_price: int
    sizes: List[dict] = Field(default_factory=list)
    flavors: List[dict] = Field(default_factory=list)
    is_active: bool = True
    images: List[ProductImage] = Field(default_factory=list)
    average_rating: Optional[float] = None
    review_count: int = 0
    created_at: datetime
    updated_at: datetime


class PaginationMeta(BaseModel):
    """Pagination metadata."""

    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_previous: bool


class ProductListResponse(BaseModel):
    """Paginated product list response."""

    products: List[ProductListItem] = Field(default_factory=list)
    pagination: PaginationMeta
