"""Admin order management API endpoints.

Endpoints:
- GET    /api/v1/admin/orders        - List all orders with filters (Admin only)
- GET    /api/v1/admin/orders/{id}   - Order detail (Admin only)
- DELETE /api/v1/admin/orders/{id}   - Cancel/reject and delete an order (Admin only)
"""

import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.dependencies import require_admin, get_supabase_client
from app.services.order_service import OrderNotFoundError, OrderService, OrderServiceError

router = APIRouter()


def _get_order_service() -> OrderService:
    """Create OrderService with Supabase client."""
    client = get_supabase_client(use_service_role=True)
    return OrderService(client)



@router.get("")
def list_admin_orders(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page (default 20)"),
    status: Optional[str] = Query(default=None, description="Filter by order status"),
    date_from: Optional[str] = Query(default=None, description="Filter orders from date (ISO format)"),
    date_to: Optional[str] = Query(default=None, description="Filter orders to date (ISO format)"),
    customer_name: Optional[str] = Query(default=None, min_length=2, description="Filter by customer name (partial, min 2 chars)"),
    admin: dict = Depends(require_admin),
):
    """
    List all orders with optional filters (Admin only).

    Filters:
    - status: pending, confirmed, in_production, ready, delivered
    - date_from / date_to: ISO date range for created_at
    - customer_name: Partial match (min 2 chars)

    Sorted by created_at descending (newest first).
    Paginated (20/page default).
    """
    supabase = get_supabase_client(use_service_role=True)

    try:
        # Build query for counting
        valid_statuses = {"pending", "confirmed", "in_production", "ready", "delivered"}
        if status and status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status. Valid values: {', '.join(valid_statuses)}")

        # Base query with exact count in a single request
        data_query = supabase.table("orders").select(
            "id, status, total_price, pickup_date, customer_name, "
            "customer_phone, customer_email, ai_summary, baker_notes, created_at, updated_at",
            count="exact"
        )

        # Apply filters
        if status:
            data_query = data_query.eq("status", status)

        if date_from:
            data_query = data_query.gte("created_at", date_from)

        if date_to:
            data_query = data_query.lte("created_at", date_to)

        if customer_name:
            # Supabase ilike for partial case-insensitive match
            pattern = f"%{customer_name}%"
            data_query = data_query.ilike("customer_name", pattern)

        # Pagination and Fetch
        offset = (page - 1) * page_size
        data_result = (
            data_query
            .order("created_at", desc=True)
            .range(offset, offset + page_size - 1)
            .execute()
        )

        orders = data_result.data or []
        total_items = data_result.count if data_result.count is not None else 0
        total_pages = math.ceil(total_items / page_size) if total_items > 0 else 0

        return {
            "orders": orders,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total_items,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Failed to fetch orders")
        raise HTTPException(status_code=500, detail="Failed to fetch orders")



@router.get("/{order_id}")
def get_admin_order_detail(
    order_id: str,
    admin: dict = Depends(require_admin),
):
    """
    Get full order detail for admin (Admin only).

    Returns complete order with customization details, AI_Summary,
    customer contact, and status history.
    """
    order_service = _get_order_service()

    try:
        result = order_service.get_order_detail(order_id, admin)
        return result
    except OrderNotFoundError:
        raise HTTPException(status_code=404, detail="Order not found")
    except OrderServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.delete("/{order_id}", status_code=204)
def delete_order(
    order_id: str,
    admin: dict = Depends(require_admin),
):
    """
    Cancel (reject) and permanently delete an order (Admin only).

    Hard-deletes the order and all related rows:
    - order_items
    - order_customizations
    - order_status_history

    This action is irreversible. Use only for rejected/invalid orders.
    """
    supabase = get_supabase_client(use_service_role=True)

    try:
        # Verify order exists first
        check = supabase.table("orders").select("id").eq("id", order_id).maybe_single().execute()
        if not check.data:
            raise HTTPException(status_code=404, detail="Order not found")

        # All child tables (order_items, cake_customizations, order_status_history, reviews)
        # have ON DELETE CASCADE, so deleting the parent row is sufficient.
        supabase.table("orders").delete().eq("id", order_id).execute()

        return None  # 204 No Content

    except HTTPException:
        raise
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Failed to delete order %s", order_id)
        raise HTTPException(status_code=500, detail="Failed to delete order")
