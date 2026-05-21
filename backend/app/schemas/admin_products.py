"""Pydantic schemas for admin product management endpoints."""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class SizeOption(BaseModel):
    """A single size option for a product."""

    name: str = Field(..., min_length=1, max_length=50, description="Size name (e.g., '16cm', '20cm')")
    price: int = Field(..., ge=1000, le=999999999, description="Price for this size in VND")


class CreateProductRequest(BaseModel):
    """Request schema for creating a new product."""

    name: str = Field(..., min_length=1, max_length=200, description="Product name")
    description: str = Field(..., min_length=1, max_length=2000, description="Product description")
    category: str = Field(..., min_length=1, max_length=100, description="Product category")
    base_price: int = Field(..., ge=1000, le=999999999, description="Base price in VND")
    sizes: list[SizeOption] = Field(..., min_length=1, max_length=10, description="Available size options")
    flavors: list[str] = Field(default=[], description="Available flavors")
    is_active: bool = Field(default=True, description="Whether product is active")

    @field_validator("name")
    @classmethod
    def validate_name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name cannot be blank")
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_description_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Description cannot be blank")
        return v.strip()

    @field_validator("category")
    @classmethod
    def validate_category_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Category cannot be blank")
        return v.strip()


class UpdateProductRequest(BaseModel):
    """Request schema for updating an existing product."""

    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Product name")
    description: Optional[str] = Field(None, min_length=1, max_length=2000, description="Product description")
    category: Optional[str] = Field(None, min_length=1, max_length=100, description="Product category")
    base_price: Optional[int] = Field(None, ge=1000, le=999999999, description="Base price in VND")
    sizes: Optional[list[SizeOption]] = Field(None, min_length=1, max_length=10, description="Available size options")
    flavors: Optional[list[str]] = Field(None, description="Available flavors")
    is_active: Optional[bool] = Field(None, description="Whether product is active")

    @field_validator("name")
    @classmethod
    def validate_name_not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Name cannot be blank")
        return v.strip() if v else v

    @field_validator("description")
    @classmethod
    def validate_description_not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Description cannot be blank")
        return v.strip() if v else v

    @field_validator("category")
    @classmethod
    def validate_category_not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Category cannot be blank")
        return v.strip() if v else v


class UpdateProductStatusRequest(BaseModel):
    """Request schema for toggling product active status."""

    is_active: bool = Field(..., description="New active status")


class ProductImageResponse(BaseModel):
    """Response schema for a product image."""

    id: str
    product_id: str
    url: str
    sort_order: int


class ProductResponse(BaseModel):
    """Response schema for a product."""

    id: str
    name: str
    description: Optional[str] = None
    category: str
    base_price: int
    sizes: list[dict] = []
    flavors: list[str] = []
    is_active: bool = True
    images: list[ProductImageResponse] = []
    created_at: str
    updated_at: str


class ProductListResponse(BaseModel):
    """Response schema for paginated product list."""

    products: list[ProductResponse]
    total: int
    page: int
    page_size: int
