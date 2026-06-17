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


class IncidentReportRequest(BaseModel):
    """Request body for reporting an incident on an order."""
    incident_type: str = Field(
        ...,
        description="Type of incident: missing_ingredient, cannot_fulfill, need_contact"
    )
    description: str = Field(
        default="",
        max_length=500,
        description="Optional description of the incident"
    )


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
def get_baker_order_detail(
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
        result = order_service.get_order_detail(order_id, baker)

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
def update_baker_notes(
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
    order_service = _get_order_service(token)

    try:
        result = order_service.update_baker_notes(order_id, body.notes, baker)
        return result
    except OrderNotFoundError:
        raise HTTPException(status_code=404, detail="Order not found")
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=403, detail=e.message)
    except OrderServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception:
        logger.exception("Failed to update baker notes for order %s", order_id)
        raise HTTPException(status_code=500, detail="Failed to update baker notes")


@router.patch("/{order_id}/status")
def update_baker_order_status(
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
        result = order_service.update_order_status(order_id, body.status, baker)
        return result
    except OrderNotFoundError:
        raise HTTPException(status_code=404, detail="Order not found")
    except InvalidStatusTransitionError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=403, detail=e.message)
    except OrderServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


VALID_INCIDENT_TYPES = {
    "missing_ingredient": "Thiếu nguyên liệu",
    "cannot_fulfill": "Không thể thực hiện",
    "need_contact": "Cần liên hệ khách",
}


@router.post("/{order_id}/incident")
def report_incident(
    order_id: str,
    body: IncidentReportRequest,
    baker: dict = Depends(require_baker),
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
):
    """
    Report an incident for an order (Baker only).

    Incident types:
    - missing_ingredient: Baker cannot find required ingredients
    - cannot_fulfill: Baker cannot produce the order as requested
    - need_contact: Baker needs to contact the customer

    Updates baker_notes with incident info so admin can see and act.
    Order must be in confirmed or in_production status.
    """
    if body.incident_type not in VALID_INCIDENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid incident_type. Must be one of: {', '.join(VALID_INCIDENT_TYPES)}",
        )

    token = credentials.credentials if credentials else None
    order_service = _get_order_service(token)

    try:
        # Get current order to verify status
        current_order = order_service.get_order_detail(order_id, baker)

        if current_order["status"] not in ("confirmed", "in_production"):
            raise HTTPException(
                status_code=400,
                detail="Chỉ có thể báo sự cố cho đơn đang được xác nhận hoặc đang làm.",
            )

        # Build incident note
        incident_label = VALID_INCIDENT_TYPES[body.incident_type]
        incident_note = f"[SỰ CỐ - {incident_label}]"
        if body.description.strip():
            incident_note += f": {body.description.strip()}"

        # Append to existing baker notes
        existing_notes = current_order.get("baker_notes") or ""
        if existing_notes:
            combined_notes = f"{incident_note}\n\n{existing_notes}"
        else:
            combined_notes = incident_note

        # Truncate to 500 chars
        if len(combined_notes) > 500:
            combined_notes = combined_notes[:497] + "..."

        result = order_service.update_baker_notes(order_id, combined_notes, baker)
        return {
            **result,
            "incident_type": body.incident_type,
            "incident_label": incident_label,
            "message": f"Đã báo sự cố: {incident_label}. Admin sẽ được thông báo.",
        }

    except HTTPException:
        raise
    except OrderNotFoundError:
        raise HTTPException(status_code=404, detail="Order not found")
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=403, detail=e.message)
    except OrderServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception:
        logger.exception("Failed to report incident for order %s", order_id)
        raise HTTPException(status_code=500, detail="Failed to report incident")
