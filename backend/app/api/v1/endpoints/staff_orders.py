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
# Đơn nháp do trợ lý tạo. Cố ý tách khỏi hàng đợi `SALES_STATUSES`: một đơn nháp
# CHƯA phải đơn tiệm đã nhận, nên không được lẫn vào đếm "cần xử lý" của quầy.
DRAFT_STATUSES = ("draft",)


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
    """Return orders that currently require action at the sales counter.

    `orders`/`pending_count`/`ready_count` chỉ gồm đơn tiệm ĐÃ nhận, giữ nguyên
    như trước. Đơn nháp của trợ lý nằm riêng ở `drafts`: trước đây danh sách cố
    ý loại `draft`, nhưng API lại cho phép chuyển `draft → pending`. Hệ quả: đơn
    trợ lý tạo ra không hiện ở đâu trong giao diện, nên nhân viên không có cách
    nào nhận nó — luồng đặt hàng qua chat bị kẹt dù backend "đã hỗ trợ".
    """
    db = get_supabase_client(use_service_role=True)
    columns = (
        "id, status, total_price, pickup_date, customer_name, "
        "customer_phone, customer_email, created_at, updated_at"
    )
    try:
        result = (
            db.table("orders")
            .select(columns)
            .in_("status", list(SALES_STATUSES))
            .order("pickup_date", desc=False)
            .execute()
        )
        orders = result.data or []

        drafts_result = (
            db.table("orders")
            .select(columns)
            .in_("status", list(DRAFT_STATUSES))
            .order("created_at", desc=True)
            .execute()
        )
        drafts = drafts_result.data or []

        return {
            "orders": orders,
            "total": len(orders),
            "pending_count": sum(1 for order in orders if order["status"] == "pending"),
            "ready_count": sum(1 for order in orders if order["status"] == "ready"),
            "drafts": drafts,
            "draft_count": len(drafts),
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
