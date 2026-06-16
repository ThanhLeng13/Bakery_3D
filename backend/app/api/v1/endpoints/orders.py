"""Order API endpoints.

Endpoints:
- POST /api/v1/orders - Create order (Customer)
- GET  /api/v1/orders - List customer orders (paginated, sorted by date desc)
- GET  /api/v1/orders/{id} - Order detail
- PATCH /api/v1/orders/{id}/status - Update order status (Admin/Baker)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials

from app.core.dependencies import get_current_user, security_scheme, get_supabase_client
from app.schemas.orders import (
    CreateOrderRequest,
    OrderDetailResponse,
    OrderListResponse,
    UpdateStatusRequest,
)
from app.services.order_service import (
    InsufficientPermissionError,
    InvalidStatusTransitionError,
    OrderNotFoundError,
    OrderService,
    OrderServiceError,
    PickupDateValidationError,
)

router = APIRouter()


def _get_order_service(token: str | None = None) -> OrderService:
    """Create OrderService with service-role Supabase client.

    Authentication is already verified upstream by get_current_user (JWT validation).
    We use the service-role client here to bypass RLS policies on the orders/order_items
    tables, which do not have permissive INSERT/UPDATE policies for authenticated users.
    """
    client = get_supabase_client(token, use_service_role=True)
    return OrderService(client)


@router.post("", status_code=201)
async def create_order(
    body: CreateOrderRequest,
    user: dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
):
    """
    Create a new order with status 'pending'.

    Requires authentication. Works for all roles.
    Validates pickup date constraints:
    - Standard cakes: at least 24h advance
    - 2-tier cakes: at least 48h advance
    - Maximum 30 days in advance

    Stores customization_json and AI_Summary when from Cake Builder.
    """
    token = credentials.credentials if credentials else None
    order_service = _get_order_service(token)

    # Convert request to dict for service layer
    order_data = {
        "full_name": body.full_name,
        "phone": body.phone,
        "email": body.email,
        "pickup_date": body.pickup_date,
        "items": [
            {
                "product_id": item.product_id,
                "size": item.size,
                "flavor": item.flavor,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "customization_json": item.customization_json,
            }
            for item in body.items
        ],
        "ai_summary": body.ai_summary,
    }

    try:
        result = await order_service.create_order(order_data, user)
        return result
    except PickupDateValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except OrderServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("", response_model=OrderListResponse)
async def list_orders(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(
        default=10, ge=1, le=50, description="Items per page (default 10)"
    ),
    user: dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
):
    """
    List the current user's own orders, paginated (10/page default), sorted by date desc.

    Requires authentication. Works for all roles (customer, baker, admin).
    Each user only sees their own orders filtered by their user ID.
    """
    token = credentials.credentials if credentials else None
    order_service = _get_order_service(token)

    try:
        result = await order_service.list_customer_orders(
            customer_id=user["id"],
            page=page,
            page_size=page_size,
        )
        return result
    except OrderServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/{order_id}", response_model=OrderDetailResponse)
async def get_order_detail(
    order_id: str,
    user: dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
):
    """
    Get full order detail by ID.

    Customers can only view their own orders.
    Admin and Baker can view any order.
    """
    token = credentials.credentials if credentials else None
    order_service = _get_order_service(token)

    try:
        result = await order_service.get_order_detail(order_id, user)
        return result
    except OrderNotFoundError:
        raise HTTPException(status_code=404, detail="Order not found")
    except OrderServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.patch("/{order_id}/status")
async def update_order_status(
    order_id: str,
    body: UpdateStatusRequest,
    user: dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
):
    """
    Update order status (Admin/Baker only).

    Valid transitions:
    - pending → confirmed (Admin only)
    - confirmed → in_production (Baker only)
    - in_production → ready (Baker only)
    - ready → delivered (Admin only)

    Invalid transitions return 400 with valid next statuses.
    Insufficient role returns 403.
    """
    token = credentials.credentials if credentials else None
    order_service = _get_order_service(token)

    try:
        result = await order_service.update_order_status(order_id, body.status, user)
        return result
    except OrderNotFoundError:
        raise HTTPException(status_code=404, detail="Order not found")
    except InvalidStatusTransitionError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=403, detail=e.message)
    except OrderServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
