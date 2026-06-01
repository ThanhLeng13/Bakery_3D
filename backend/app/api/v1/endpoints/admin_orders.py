"""Admin order management API endpoints.

Endpoints:
- GET /api/v1/admin/orders - List all orders with filters (Admin only)
- GET /api/v1/admin/orders/{id} - Order detail (Admin only)
"""

import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.config import settings
from app.core.dependencies import require_admin
from app.services.order_service import OrderNotFoundError, OrderService, OrderServiceError

router = APIRouter()


def _get_supabase_client():
    """Get Supabase admin client (service role) to bypass RLS.
    Auth is enforced via require_admin dependency at the route level.
    """
    from supabase import create_client

    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def _get_order_service() -> OrderService:
    """Create OrderService with Supabase client."""
    client = _get_supabase_client()
    return OrderService(client)


@router.get("")
async def list_admin_orders(
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
    supabase = _get_supabase_client()

    try:
        # Build query for counting
        valid_statuses = {"pending", "confirmed", "in_production", "ready", "delivered"}
        if status and status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status. Valid values: {', '.join(valid_statuses)}")

        # Base query
        count_query = supabase.table("orders").select("id", count="exact")
        data_query = supabase.table("orders").select(
            "id, status, total_price, pickup_date, customer_name, "
            "customer_phone, customer_email, ai_summary, baker_notes, created_at, updated_at"
        )

        # Apply filters
        if status:
            count_query = count_query.eq("status", status)
            data_query = data_query.eq("status", status)

        if date_from:
            count_query = count_query.gte("created_at", date_from)
            data_query = data_query.gte("created_at", date_from)

        if date_to:
            count_query = count_query.lte("created_at", date_to)
            data_query = data_query.lte("created_at", date_to)

        if customer_name:
            # Supabase ilike for partial case-insensitive match
            pattern = f"%{customer_name}%"
            count_query = count_query.ilike("customer_name", pattern)
            data_query = data_query.ilike("customer_name", pattern)

        # Count total
        count_result = count_query.execute()
        total_items = count_result.count if count_result.count is not None else 0

        # Pagination
        total_pages = math.ceil(total_items / page_size) if total_items > 0 else 0
        offset = (page - 1) * page_size

        # Fetch data
        data_result = (
            data_query
            .order("created_at", desc=True)
            .range(offset, offset + page_size - 1)
            .execute()
        )

        orders = data_result.data or []

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
        raise HTTPException(status_code=500, detail="Failed to fetch orders")


@router.get("/{order_id}")
async def get_admin_order_detail(
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
        result = await order_service.get_order_detail(order_id, admin)
        return result
    except OrderNotFoundError:
        raise HTTPException(status_code=404, detail="Order not found")
    except OrderServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
