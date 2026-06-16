"""Order service - business logic for order CRUD and status management.

Handles order creation, listing, detail retrieval, and status transitions.
Enforces pickup date validation and role-based status transition rules.
"""

import logging
import math
from datetime import datetime, timezone
from typing import Any

_logger = logging.getLogger(__name__)


class OrderServiceError(Exception):
    """Base exception for order service errors."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class OrderNotFoundError(OrderServiceError):
    """Order not found."""

    def __init__(self, order_id: str):
        super().__init__(f"Order not found: {order_id}", status_code=404)


class InvalidStatusTransitionError(OrderServiceError):
    """Invalid order status transition."""

    def __init__(self, current_status: str, requested_status: str, valid_next: list[str]):
        valid_str = ", ".join(valid_next) if valid_next else "none"
        super().__init__(
            f"Cannot transition from '{current_status}' to '{requested_status}'. "
            f"Valid next statuses: {valid_str}",
            status_code=400,
        )


class InsufficientPermissionError(OrderServiceError):
    """User does not have permission for this status transition."""

    def __init__(self, role: str, transition: str):
        super().__init__(
            f"Role '{role}' is not allowed to perform transition: {transition}",
            status_code=403,
        )


class PickupDateValidationError(OrderServiceError):
    """Pickup date does not meet requirements."""

    def __init__(self, message: str):
        super().__init__(message, status_code=400)


# Valid status transitions and required roles
VALID_TRANSITIONS: dict[str, dict[str, list[str]]] = {
    "pending": {"confirmed": ["admin"]},
    "confirmed": {"in_production": ["baker"]},
    "in_production": {"ready": ["baker"]},
    "ready": {"delivered": ["admin"]},
}


def get_valid_next_statuses(current_status: str) -> list[str]:
    """Get list of valid next statuses for a given current status."""
    transitions = VALID_TRANSITIONS.get(current_status, {})
    return list(transitions.keys())


def get_allowed_roles_for_transition(current_status: str, new_status: str) -> list[str]:
    """Get roles allowed to perform a specific transition."""
    transitions = VALID_TRANSITIONS.get(current_status, {})
    return transitions.get(new_status, [])


class OrderService:
    """Order service for managing orders in Supabase."""

    def __init__(self, supabase_client: Any):
        """Initialize with a Supabase client instance."""
        self._supabase = supabase_client

    def _check_baker_authorization(self, order_id: str, order: dict, baker: dict, read_only: bool = False) -> None:
        """
        Verify that the baker is authorized to access or modify this order.
        Prevents Broken Object Level Authorization (BOLA) when RLS is bypassed.
        If read_only is True, bypasses the ownership check.
        """
        if baker.get("role") != "baker":
            return
            
        # 1. Branch-level check (if branch_id exists in future schemas)
        baker_branch = baker.get("branch_id") or (baker.get("user_metadata") or {}).get("branch_id")
        order_branch = order.get("branch_id")
        if baker_branch and order_branch and baker_branch != order_branch:
            raise InsufficientPermissionError("baker", "access orders from another branch")
            
        # 2. Explicit ownership check (baker who claimed the order)
        if not read_only and order.get("status") in ("in_production", "ready"):
            history = (
                self._supabase.table("order_status_history")
                .select("changed_by")
                .eq("order_id", order_id)
                .eq("new_status", "in_production")
                .order("changed_at", desc=False)
                .limit(1)
                .execute()
            )
            if history.data:
                claiming_baker = history.data[0].get("changed_by")
                if claiming_baker and claiming_baker != baker.get("id"):
                    raise InsufficientPermissionError("baker", "modify an order claimed by another baker")

    def _validate_pickup_date(self, pickup_date: datetime, items: list[dict]) -> None:
        """
        Validate pickup date constraints.

        Rules:
        - Standard cakes: at least 24 hours from now
        - 2-tier cakes: at least 48 hours from now
        - Maximum 30 days in advance
        """
        now = datetime.now(timezone.utc)

        # Ensure pickup_date is timezone-aware
        if pickup_date.tzinfo is None:
            pickup_date = pickup_date.replace(tzinfo=timezone.utc)

        hours_until_pickup = (pickup_date - now).total_seconds() / 3600
        days_until_pickup = (pickup_date - now).total_seconds() / (3600 * 24)

        # Check maximum advance booking (30 days)
        if days_until_pickup > 30:
            raise PickupDateValidationError(
                "Pickup date must be within 30 days from now."
            )

        # Check if any item is 2-tier
        has_two_tier = any(
            item.get("size", "").lower() in ("2-tier", "2 tier", "2tier")
            for item in items
        )

        if has_two_tier:
            if hours_until_pickup < 48:
                raise PickupDateValidationError(
                    "2-tier cakes require at least 48 hours advance notice. "
                    "Please select a later pickup date."
                )
        else:
            if hours_until_pickup < 24:
                raise PickupDateValidationError(
                    "Standard cakes require at least 24 hours advance notice. "
                    "Please select a later pickup date."
                )

    def create_order(self, order_data: dict, customer: dict) -> dict:
        """
        Create a new order with status 'pending'.

        Args:
            order_data: Dict with full_name, phone, email, pickup_date, items, ai_summary
            customer: Current user dict from auth dependency

        Returns:
            Created order dict with id and status

        Raises:
            PickupDateValidationError: If pickup date doesn't meet constraints
            OrderServiceError: If order creation fails
        """
        items = order_data["items"]

        # Validate pickup date
        self._validate_pickup_date(order_data["pickup_date"], items)

        # Calculate total price
        total_price = sum(item["unit_price"] * item["quantity"] for item in items)

        # Create order record
        order_insert = {
            "customer_id": customer["id"],
            "status": "pending",
            "total_price": total_price,
            "pickup_date": order_data["pickup_date"].isoformat(),
            "customer_name": order_data["full_name"],
            "customer_phone": order_data["phone"],
            "customer_email": order_data.get("email"),
            "ai_summary": order_data.get("ai_summary"),
        }

        order_result = (
            self._supabase.table("orders")
            .insert(order_insert)
            .execute()
        )

        if not order_result.data:
            raise OrderServiceError("Failed to create order", status_code=500)

        order = order_result.data[0]
        order_id = order["id"]

        # Create order items
        for item in items:
            # Cake Builder custom cakes use a null/placeholder UUID
            # (00000000-0000-0000-0000-000000000000) because they are not a
            # catalog product. Store as NULL to avoid FK constraint violations.
            NULL_UUID = "00000000-0000-0000-0000-000000000000"
            raw_pid = item.get("product_id")
            # Treat Python None AND the placeholder UUID both as NULL in DB.
            # Calling str(None) would produce the literal string "None" which
            # causes a UUID column constraint error.
            product_id_value = None if (raw_pid is None or str(raw_pid) == NULL_UUID) else str(raw_pid)

            item_insert = {
                "order_id": order_id,
                "product_id": product_id_value,
                "size": item.get("size"),
                "flavor": item.get("flavor"),
                "quantity": item["quantity"],
                "unit_price": item["unit_price"],
            }

            item_result = (
                self._supabase.table("order_items")
                .insert(item_insert)
                .execute()
            )

            if not item_result.data:
                raise OrderServiceError("Failed to create order item", status_code=500)

            order_item_id = item_result.data[0]["id"]

            # Create cake customization if present
            if item.get("customization_json"):
                customization_insert = {
                    "order_id": order_id,
                    "order_item_id": order_item_id,
                    "customization_json": item["customization_json"],
                }

                self._supabase.table("cake_customizations").insert(
                    customization_insert
                ).execute()

        # Record initial status in history
        changed_by_id = customer.get("id") or None
        self._supabase.table("order_status_history").insert({
            "order_id": order_id,
            "old_status": None,
            "new_status": "pending",
            "changed_by": changed_by_id,
        }).execute()

        return order

    def list_customer_orders(
        self,
        customer_id: str,
        page: int = 1,
        page_size: int = 10,
    ) -> dict:
        """
        List orders for a specific customer, paginated and sorted by date desc.

        Args:
            customer_id: UUID string of the customer
            page: Page number (1-indexed)
            page_size: Items per page (default 10)

        Returns:
            Dict with orders list and pagination metadata
        """
        # Count total orders for this customer
        count_result = (
            self._supabase.table("orders")
            .select("id", count="exact")
            .eq("customer_id", customer_id)
            .execute()
        )
        total_items = count_result.count if count_result.count is not None else 0

        # Calculate pagination
        total_pages = math.ceil(total_items / page_size) if total_items > 0 else 0
        offset = (page - 1) * page_size

        # Fetch orders
        data_result = (
            self._supabase.table("orders")
            .select(
                "id, status, total_price, pickup_date, customer_name, "
                "customer_phone, created_at"
            )
            .eq("customer_id", customer_id)
            .order("created_at", desc=True)
            .range(offset, offset + page_size - 1)
            .execute()
        )

        orders = data_result.data or []

        pagination = {
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1,
        }

        return {
            "orders": orders,
            "pagination": pagination,
        }

    def get_order_detail(self, order_id: str, user: dict) -> dict:
        """
        Get full order detail by ID.

        Customers can only view their own orders.
        Admin and Baker can view any order.

        Args:
            order_id: UUID string of the order
            user: Current user dict

        Returns:
            Dict with full order detail

        Raises:
            OrderNotFoundError: If order not found or access denied
        """
        # Fetch order
        order_result = (
            self._supabase.table("orders")
            .select("*")
            .eq("id", order_id)
            .maybe_single()
            .execute()
        )

        if order_result is None or order_result.data is None:
            raise OrderNotFoundError(order_id)

        order = order_result.data

        # Check access: customers can only see their own orders
        if user["role"] == "customer" and order["customer_id"] != user["id"]:
            raise OrderNotFoundError(order_id)
            
        # Validate baker authorization
        self._check_baker_authorization(order_id, order, user, read_only=True)

        # Fetch order items
        items_result = (
            self._supabase.table("order_items")
            .select("id, product_id, size, flavor, quantity, unit_price, created_at")
            .eq("order_id", order_id)
            .order("created_at", desc=False)
            .execute()
        )
        items = items_result.data or []

        # Fetch cake customizations
        customizations_result = (
            self._supabase.table("cake_customizations")
            .select("id, order_item_id, customization_json, preview_image_url, created_at")
            .eq("order_id", order_id)
            .execute()
        )
        customizations = customizations_result.data or []

        # Fetch status history
        history_result = (
            self._supabase.table("order_status_history")
            .select("id, old_status, new_status, changed_by, changed_at")
            .eq("order_id", order_id)
            .order("changed_at", desc=False)
            .execute()
        )
        status_history = history_result.data or []

        return {
            "id": order["id"],
            "customer_id": order["customer_id"],
            "status": order["status"],
            "total_price": order["total_price"],
            "pickup_date": order["pickup_date"],
            "customer_name": order["customer_name"],
            "customer_phone": order["customer_phone"],
            "customer_email": order.get("customer_email"),
            "ai_summary": order.get("ai_summary"),
            "baker_notes": order.get("baker_notes"),
            "items": items,
            "customizations": customizations,
            "status_history": status_history,
            "created_at": order["created_at"],
            "updated_at": order["updated_at"],
        }

    def update_order_status(
        self, order_id: str, new_status: str, user: dict
    ) -> dict:
        """
        Update order status with state machine validation and role enforcement.

        Valid transitions:
        - pending → confirmed (Admin only)
        - confirmed → in_production (Baker only)
        - in_production → ready (Baker only)
        - ready → delivered (Admin only)

        Args:
            order_id: UUID string of the order
            new_status: Target status
            user: Current user dict (must have role field)

        Returns:
            Updated order dict

        Raises:
            OrderNotFoundError: If order not found
            InvalidStatusTransitionError: If transition is not valid
            InsufficientPermissionError: If user role cannot perform transition
        """
        # Fetch current order (include total_price for loyalty award on delivery)
        order_result = (
            self._supabase.table("orders")
            .select("id, status, customer_id, total_price")
            .eq("id", order_id)
            .maybe_single()
            .execute()
        )

        if order_result is None or order_result.data is None:
            raise OrderNotFoundError(order_id)

        order = order_result.data
        current_status = order["status"]

        # Validate transition
        valid_next = get_valid_next_statuses(current_status)
        if new_status not in valid_next:
            raise InvalidStatusTransitionError(current_status, new_status, valid_next)

        # Validate role permission
        allowed_roles = get_allowed_roles_for_transition(current_status, new_status)
        user_role = user.get("role", "")
        if user_role not in allowed_roles:
            raise InsufficientPermissionError(
                user_role, f"{current_status} → {new_status}"
            )

        # Validate baker authorization
        self._check_baker_authorization(order_id, order, user)

        # Perform the update
        update_result = (
            self._supabase.table("orders")
            .update({"status": new_status, "updated_at": datetime.now(timezone.utc).isoformat()})
            .eq("id", order_id)
            .execute()
        )

        if not update_result.data:
            raise OrderServiceError("Failed to update order status", status_code=500)

        # Record status change in history
        changed_by_id = user.get("id") or None
        self._supabase.table("order_status_history").insert({
            "order_id": order_id,
            "old_status": current_status,
            "new_status": new_status,
            "changed_by": changed_by_id,
        }).execute()

        # Cộng điểm tích lũy khi order giao thành công
        if new_status == "delivered":
            try:
                from app.services.loyalty_service import LoyaltyService
                from app.core.dependencies import get_supabase_client
                
                # total_price và customer_id đã có trong `order` (SELECT đã bao gồm)
                total_price = order.get("total_price") or 0
                customer_id = order.get("customer_id")
                if customer_id and total_price:
                    # Phải dùng service_role client vì bảng loyalty_points
                    # bị chặn RLS ghi đối với user thường (kể cả baker/admin user_id)
                    admin_client = get_supabase_client(use_service_role=True)
                    loyalty_svc = LoyaltyService(admin_client)
                    
                    loyalty_svc.award_points(
                        user_id=customer_id,
                        amount_vnd=int(total_price),
                        source_type="order",
                        ref_id=order_id,
                    )
            except Exception as loyalty_err:
                _logger.warning(
                    "Không thể cộng điểm cho order %s: %s", order_id, loyalty_err
                )

        return update_result.data[0]

    def update_baker_notes(self, order_id: str, notes: str, user: dict) -> dict:
        """Update baker notes for an order."""
        order_result = (
            self._supabase.table("orders")
            .select("*")
            .eq("id", order_id)
            .maybe_single()
            .execute()
        )

        if order_result is None or order_result.data is None:
            raise OrderNotFoundError(order_id)

        order = order_result.data
        if order["status"] not in ("confirmed", "in_production", "ready"):
            raise OrderServiceError(
                "Baker notes can only be updated for orders in confirmed, in_production, or ready status",
                status_code=400
            )

        self._check_baker_authorization(order_id, order, user)

        update_result = (
            self._supabase.table("orders")
            .update({"baker_notes": notes})
            .eq("id", order_id)
            .execute()
        )

        if not update_result.data:
            raise OrderServiceError("Failed to update baker notes", status_code=500)

        return {
            "id": order_id,
            "baker_notes": notes,
            "message": "Baker notes updated successfully",
        }
