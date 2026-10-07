"""Pydantic schemas for order endpoints."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# --- Request Schemas ---


class OrderItemRequest(BaseModel):
    """Single item in an order."""

    product_id: UUID
    size: Optional[str] = None
    flavor: Optional[str] = None
    quantity: int = Field(default=1, ge=1)
    unit_price: int = Field(ge=1000, description="Unit price in VND")
    customization_json: Optional[Dict[str, Any]] = None


class CreateOrderRequest(BaseModel):
    """Request body for creating a new order."""

    full_name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=10, max_length=10)
    email: Optional[str] = Field(default=None, max_length=254)
    pickup_date: datetime
    items: List[OrderItemRequest] = Field(min_length=1)
    ai_summary: Optional[str] = None
    voucher_code: Optional[str] = Field(
        default=None,
        max_length=64,
        description=(
            "Mã voucher khách nhập. Mức giảm đọc từ bảng `vouchers` ở server, "
            "không nhận từ phía trình duyệt."
        ),
    )

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not v.isdigit() or len(v) != 10:
            raise ValueError("Phone must be exactly 10 digits")
        return v

    @field_validator("voucher_code")
    @classmethod
    def normalize_voucher_code(cls, v: Optional[str]) -> Optional[str]:
        """Mã không phân biệt hoa thường, bỏ khoảng trắng thừa."""
        if v is None:
            return None
        clean = v.strip().upper()
        return clean or None


class UpdateStatusRequest(BaseModel):
    """Request body for updating order status."""

    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        # 'draft' is a valid stored status but nothing transitions *into* it:
        # only the agent creates drafts, and it creates them directly. Staff
        # move a draft to 'pending' to accept it.
        valid_statuses = [
            "draft",
            "pending",
            "confirmed",
            "in_production",
            "ready",
            "delivered",
        ]
        if v not in valid_statuses:
            raise ValueError(
                f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )
        return v


class QuoteRequest(BaseModel):
    """Báo giá một chiếc bánh tùy chỉnh mà chưa lưu đơn."""

    design: Dict[str, Any] = Field(
        ...,
        description="Cấu hình CakeDesign: size, topping_type, zones (top/body/border).",
    )


class QuoteResponse(BaseModel):
    """Giá do server quyết định, gồm từng khoản để hiển thị."""

    base_price: int = Field(..., description="Giá theo kích cỡ (VND).")
    topping_cost: int = Field(..., description="Tổng phí topping (VND).")
    decoration_cost: int = Field(..., description="Tổng phí trang trí (VND).")
    total: int = Field(..., description="Tổng tiền sẽ ghi vào đơn (VND).")
    lead_hours: int = Field(..., description="Giờ chuẩn bị tối thiểu theo kích cỡ.")


# --- Response Schemas ---


class OrderItemResponse(BaseModel):
    """Order item in response."""

    id: UUID
    product_id: UUID
    size: Optional[str] = None
    flavor: Optional[str] = None
    quantity: int
    unit_price: int
    created_at: datetime


class CakeCustomizationResponse(BaseModel):
    """Cake customization in response."""

    id: UUID
    order_item_id: Optional[UUID] = None
    customization_json: Dict[str, Any]
    preview_image_url: Optional[str] = None
    created_at: datetime


class StatusHistoryEntry(BaseModel):
    """Single entry in order status history."""

    id: UUID
    old_status: Optional[str] = None
    new_status: str
    changed_by: UUID
    changed_at: datetime


class OrderListItem(BaseModel):
    """Order item in list view."""

    id: UUID
    status: str
    total_price: int
    pickup_date: datetime
    customer_name: str
    customer_phone: str
    created_at: datetime


class OrderDetailResponse(BaseModel):
    """Full order detail response."""

    id: UUID
    customer_id: UUID
    status: str
    total_price: int
    pickup_date: datetime
    customer_name: str
    customer_phone: str
    customer_email: Optional[str] = None
    ai_summary: Optional[str] = None
    baker_notes: Optional[str] = None
    voucher_code: Optional[str] = None
    voucher_discount: int = 0
    items: List[OrderItemResponse] = Field(default_factory=list)
    customizations: List[CakeCustomizationResponse] = Field(default_factory=list)
    status_history: List[StatusHistoryEntry] = Field(default_factory=list)
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


class OrderListResponse(BaseModel):
    """Paginated order list response."""

    orders: List[OrderListItem] = Field(default_factory=list)
    pagination: PaginationMeta
