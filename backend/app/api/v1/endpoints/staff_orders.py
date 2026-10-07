"""Sales staff order queue.

Staff only handle the two customer-facing hand-off steps:
- pending -> confirmed
- ready -> delivered

Production steps remain exclusive to bakers.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.core.dependencies import get_supabase_client, require_staff
from app.services.order_service import (
    InsufficientPermissionError,
    InvalidStatusTransitionError,
    OrderNotFoundError,
    OrderService,
    OrderServiceError,
)

router = APIRouter()
# Trạng thái còn cần nhân viên bán hàng xử lý. 'draft' có mặt để staff MỞ
# ĐƯỢC đơn nháp của agent và xác nhận; nó không xuất hiện trong danh sách
# liệt kê, nên đơn nháp không lọt vào hàng đợi như một đơn đã nhận.
SALES_STATUSES = ("pending", "ready")
# Staff cần đọc đơn nháp để quyết định có nhận hay không.
READABLE_STATUSES = ("draft", "pending", "ready")


class StaffStatusRequest(BaseModel):
    status: str = Field(
        ...,
        description=(
            "New status: pending to accept an agent draft, confirmed to start "
            "production, or delivered to hand over."
        ),
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        # 'pending' accepts a draft the agent created from a conversation:
        # staff take responsibility for it. 'confirmed' and 'delivered' move a
        # real order along.
        if value not in {"pending", "confirmed", "delivered"}:
            raise ValueError(
                "Staff may only accept a draft, confirm an order, or deliver it"
            )
        return value


def _get_order_service() -> OrderService:
    return OrderService(get_supabase_client(use_service_role=True))


@router.get("")
def list_sales_orders(staff: dict = Depends(require_staff)):
    """Return orders that currently require action at the sales counter."""
    db = get_supabase_client(use_service_role=True)
    try:
        result = (
            db.table("orders")
            .select(
                "id, status, total_price, pickup_date, customer_name, "
                "customer_phone, customer_email, created_at, updated_at"
            )
            .in_("status", list(SALES_STATUSES))
            .order("pickup_date", desc=False)
            .execute()
        )
        orders = result.data or []
        return {
            "orders": orders,
            "total": len(orders),
            "pending_count": sum(1 for order in orders if order["status"] == "pending"),
            "ready_count": sum(1 for order in orders if order["status"] == "ready"),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Không thể tải hàng đợi bán hàng.") from exc


@router.get("/{order_id}")
def get_sales_order(order_id: str, staff: dict = Depends(require_staff)):
    """Return full detail for an order currently handled by sales staff."""
    service = _get_order_service()
    try:
        order = service.get_order_detail(order_id, staff)
        if order["status"] not in READABLE_STATUSES:
            raise HTTPException(status_code=403, detail="Đơn hàng không thuộc hàng đợi bán hàng.")
        return order
    except HTTPException:
        raise
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Order not found") from exc
    except OrderServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.patch("/{order_id}/status")
def update_sales_order_status(
    order_id: str,
    body: StaffStatusRequest,
    staff: dict = Depends(require_staff),
):
    """Confirm a new order or mark a ready order as delivered."""
    service = _get_order_service()
    try:
        return service.update_order_status(order_id, body.status, staff)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Order not found") from exc
    except InvalidStatusTransitionError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc
    except InsufficientPermissionError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc
    except OrderServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
