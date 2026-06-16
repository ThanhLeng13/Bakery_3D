"""Baker order management API endpoints.

Endpoints:
- GET /api/v1/baker/orders - List orders (confirmed + in_production), sorted by pickup_date asc (Baker only)
- GET /api/v1/baker/orders/{id} - Order detail (Baker only)
- PATCH /api/v1/baker/orders/{id}/notes - Update baker notes (Baker only)
- PATCH /api/v1/baker/orders/{id}/status - Update status confirmed→in_production, in_production→ready (Baker only)
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from app.core.dependencies import require_baker, security_scheme, get_supabase_client
from app.core.logging import get_logger
from app.services.order_service import (
    InsufficientPermissionError,
    InvalidStatusTransitionError,
    OrderNotFoundError,
    OrderService,
    OrderServiceError,
)

router = APIRouter()
logger = get_logger(__name__)


class BakerNotesRequest(BaseModel):
    """Request body for updating baker notes."""
    notes: str = Field(..., max_length=500, description="Baker notes (max 500 chars)")


class BakerStatusRequest(BaseModel):
    """Request body for baker status update."""
    status: str = Field(..., description="New status: in_production or ready")


def _get_order_service(token: str | None = None) -> OrderService:
    """Create OrderService with service-role Supabase client.

    Authentication is already verified upstream by require_baker (JWT validation).
    We use the service-role client here to bypass RLS policies.
    """
    client = get_supabase_client(token, use_service_role=True)
    return OrderService(client)


@router.get("")
def list_baker_orders(
    baker: dict = Depends(require_baker),
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
):
    """
    List orders with status 'confirmed' or 'in_production' (Baker only).

    Sorted by pickup_date ascending so baker sees most urgent orders first.
    Returns complete order info including customization details and AI summary.
    """
    token = credentials.credentials if credentials else None
    supabase = get_supabase_client(token, use_service_role=True)

    try:
        result = (
            supabase.table("orders")
            .select(
                "id, status, total_price, pickup_date, customer_name, "
                "customer_phone, ai_summary, baker_notes, created_at, updated_at"
            )
            .in_("status", ["confirmed", "in_production"])
            .order("pickup_date", desc=False)
            .execute()
        )

        orders = result.data or []
        return {"orders": orders, "total": len(orders)}

    except Exception:
        logger.exception("Failed to fetch baker orders")
        raise HTTPException(status_code=500, detail="Failed to fetch baker orders")


@router.get("/{order_id}")
async def get_baker_order_detail(
    order_id: str,
    baker: dict = Depends(require_baker),
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
):
    """
    Get full order detail for baker (Baker only).

    Returns order with customization details, AI_Summary, baker_notes,
    and pickup date for production planning.
    """
    token = credentials.credentials if credentials else None
    order_service = _get_order_service(token)

    try:
        result = await order_service.get_order_detail(order_id, baker)

        # Verify order is in baker-accessible status
        if result["status"] not in ("confirmed", "in_production", "ready"):
            raise HTTPException(
                status_code=403,
                detail="Order is not in a status accessible to bakers",
            )

        return result
    except HTTPException:
        raise
    except OrderNotFoundError:
        raise HTTPException(status_code=404, detail="Order not found")
    except OrderServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.patch("/{order_id}/notes")
async def update_baker_notes(
    order_id: str,
    body: BakerNotesRequest,
    baker: dict = Depends(require_baker),
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
):
    """
    Add or update baker notes for an order (Baker only).

    Notes max 500 characters. Order must be in confirmed or in_production status.
    """
    token = credentials.credentials if credentials else None
    supabase = get_supabase_client(token, use_service_role=True)

    try:
        # Verify order exists and is accessible
        order_result = (
            supabase.table("orders")
            .select("id, status")
            .eq("id", order_id)
            .maybe_single()
            .execute()
        )

        if order_result is None or order_result.data is None:
            raise HTTPException(status_code=404, detail="Order not found")

        order = order_result.data
        if order["status"] not in ("confirmed", "in_production", "ready"):
            raise HTTPException(
                status_code=400,
                detail="Baker notes can only be updated for orders in confirmed, in_production, or ready status",
            )

        # Update baker notes
        update_result = (
            supabase.table("orders")
            .update({"baker_notes": body.notes})
            .eq("id", order_id)
            .execute()
        )

        if not update_result.data:
            raise HTTPException(status_code=500, detail="Failed to update baker notes")

        return {
            "id": order_id,
            "baker_notes": body.notes,
            "message": "Baker notes updated successfully",
        }

    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to update baker notes for order %s", order_id)
        raise HTTPException(status_code=500, detail="Failed to update baker notes")


@router.patch("/{order_id}/status")
async def update_baker_order_status(
    order_id: str,
    body: BakerStatusRequest,
    baker: dict = Depends(require_baker),
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
):
    """
    Update order status (Baker only).

    Valid transitions for baker:
    - confirmed → in_production
    - in_production → ready

    Invalid transitions return 400 with valid next statuses.
    """
    token = credentials.credentials if credentials else None
    order_service = _get_order_service(token)

    # Validate allowed baker statuses
    baker_allowed_statuses = {"in_production", "ready"}
    if body.status not in baker_allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Baker can only set status to: {', '.join(baker_allowed_statuses)}",
        )

    try:
        result = await order_service.update_order_status(order_id, body.status, baker)
        return result
    except OrderNotFoundError:
        raise HTTPException(status_code=404, detail="Order not found")
    except InvalidStatusTransitionError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=403, detail=e.message)
    except OrderServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
