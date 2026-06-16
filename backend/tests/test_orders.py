"""Tests for order service and schemas.

Tests cover:
- Order creation validation (required fields, pickup date)
- Pickup date validation (24h standard, 48h 2-tier, 30 day max)
- Order status state machine transitions
- Role-based permission enforcement for status updates
- Order listing pagination
- Schema validation
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.schemas.orders import (
    CreateOrderRequest,
    OrderDetailResponse,
    OrderListItem,
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
    get_allowed_roles_for_transition,
    get_valid_next_statuses,
)


# ============================================================
# Status State Machine Tests
# ============================================================


class TestStatusStateMachine:
    """Test order status state machine logic."""

    def test_pending_valid_next_is_confirmed(self):
        assert get_valid_next_statuses("pending") == ["confirmed"]

    def test_confirmed_valid_next_is_in_production(self):
        assert get_valid_next_statuses("confirmed") == ["in_production"]

    def test_in_production_valid_next_is_ready(self):
        assert get_valid_next_statuses("in_production") == ["ready"]

    def test_ready_valid_next_is_delivered(self):
        assert get_valid_next_statuses("ready") == ["delivered"]

    def test_delivered_has_no_valid_next(self):
        assert get_valid_next_statuses("delivered") == []

    def test_unknown_status_has_no_valid_next(self):
        assert get_valid_next_statuses("unknown") == []

    def test_pending_to_confirmed_requires_admin(self):
        assert get_allowed_roles_for_transition("pending", "confirmed") == ["admin"]

    def test_confirmed_to_in_production_requires_baker(self):
        assert get_allowed_roles_for_transition("confirmed", "in_production") == ["baker"]

    def test_in_production_to_ready_requires_baker(self):
        assert get_allowed_roles_for_transition("in_production", "ready") == ["baker"]

    def test_ready_to_delivered_requires_admin(self):
        assert get_allowed_roles_for_transition("ready", "delivered") == ["admin"]

    def test_invalid_transition_returns_empty_roles(self):
        assert get_allowed_roles_for_transition("pending", "delivered") == []

    def test_reverse_transition_returns_empty_roles(self):
        assert get_allowed_roles_for_transition("confirmed", "pending") == []


# ============================================================
# Pickup Date Validation Tests
# ============================================================


class TestPickupDateValidation:
    """Test pickup date validation logic."""

    def setup_method(self):
        self.mock_supabase = MagicMock()
        self.service = OrderService(self.mock_supabase)

    def test_standard_cake_24h_minimum(self):
        """Standard cakes need at least 24h advance."""
        pickup = datetime.now(timezone.utc) + timedelta(hours=23)
        items = [{"size": "20cm", "unit_price": 100000, "quantity": 1}]

        with pytest.raises(PickupDateValidationError) as exc_info:
            self.service._validate_pickup_date(pickup, items)
        assert "24 hours" in exc_info.value.message

    def test_standard_cake_24h_passes(self):
        """Standard cakes with 24h+ advance should pass."""
        pickup = datetime.now(timezone.utc) + timedelta(hours=25)
        items = [{"size": "20cm", "unit_price": 100000, "quantity": 1}]

        # Should not raise
        self.service._validate_pickup_date(pickup, items)

    def test_two_tier_cake_48h_minimum(self):
        """2-tier cakes need at least 48h advance."""
        pickup = datetime.now(timezone.utc) + timedelta(hours=30)
        items = [{"size": "2-tier", "unit_price": 500000, "quantity": 1}]

        with pytest.raises(PickupDateValidationError) as exc_info:
            self.service._validate_pickup_date(pickup, items)
        assert "48 hours" in exc_info.value.message

    def test_two_tier_cake_48h_passes(self):
        """2-tier cakes with 48h+ advance should pass."""
        pickup = datetime.now(timezone.utc) + timedelta(hours=49)
        items = [{"size": "2-tier", "unit_price": 500000, "quantity": 1}]

        # Should not raise
        self.service._validate_pickup_date(pickup, items)

    def test_max_30_days_advance(self):
        """Pickup date cannot be more than 30 days in advance."""
        pickup = datetime.now(timezone.utc) + timedelta(days=31)
        items = [{"size": "20cm", "unit_price": 100000, "quantity": 1}]

        with pytest.raises(PickupDateValidationError) as exc_info:
            self.service._validate_pickup_date(pickup, items)
        assert "30 days" in exc_info.value.message

    def test_within_30_days_passes(self):
        """Pickup date within 30 days should pass."""
        pickup = datetime.now(timezone.utc) + timedelta(days=29)
        items = [{"size": "20cm", "unit_price": 100000, "quantity": 1}]

        # Should not raise
        self.service._validate_pickup_date(pickup, items)

    def test_naive_datetime_treated_as_utc(self):
        """Naive datetime should be treated as UTC."""
        pickup = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=25)
        items = [{"size": "20cm", "unit_price": 100000, "quantity": 1}]

        # Should not raise (treated as UTC, 25h ahead)
        self.service._validate_pickup_date(pickup, items)


# ============================================================
# Order Service - Create Order Tests
# ============================================================


class TestCreateOrder:
    """Test order creation logic."""

    def setup_method(self):
        self.mock_supabase = MagicMock()
        self.service = OrderService(self.mock_supabase)
        self.customer = {
            "id": str(uuid4()),
            "email": "customer@test.com",
            "full_name": "Test Customer",
            "phone": "0901234567",
            "role": "customer",
        }

    def _mock_insert_chain(self, table_name, return_data):
        """Helper to mock supabase.table(name).insert(...).execute()."""
        mock_table = MagicMock()
        mock_insert = MagicMock()
        mock_execute = MagicMock()
        mock_execute.data = return_data

        self.mock_supabase.table.return_value = mock_table
        mock_table.insert.return_value = mock_insert
        mock_insert.execute.return_value = mock_execute

        return mock_execute

    def test_create_order_calculates_total_price(self):
        """Total price should be sum of (unit_price * quantity) for all items."""
        order_id = str(uuid4())
        item_id = str(uuid4())

        # Mock all table operations
        mock_table = MagicMock()
        self.mock_supabase.table.return_value = mock_table

        # Mock insert().execute() for orders
        mock_insert = MagicMock()
        mock_table.insert.return_value = mock_insert
        mock_insert.execute.return_value = MagicMock(
            data=[{"id": order_id, "status": "pending", "total_price": 350000}]
        )

        order_data = {
            "full_name": "Test",
            "phone": "0901234567",
            "email": None,
            "pickup_date": datetime.now(timezone.utc) + timedelta(hours=25),
            "items": [
                {"product_id": uuid4(), "size": "20cm", "flavor": "chocolate",
                 "quantity": 2, "unit_price": 150000, "customization_json": None},
                {"product_id": uuid4(), "size": "16cm", "flavor": "vanilla",
                 "quantity": 1, "unit_price": 50000, "customization_json": None},
            ],
            "ai_summary": None,
        }

        result = self.service.create_order(order_data, self.customer)

        # Verify the insert was called with correct total_price
        insert_call = mock_table.insert.call_args_list[0]
        inserted_data = insert_call[0][0]
        assert inserted_data["total_price"] == 350000  # 150000*2 + 50000*1

    def test_create_order_stores_ai_summary(self):
        """AI summary should be stored in the order record."""
        order_id = str(uuid4())

        mock_table = MagicMock()
        self.mock_supabase.table.return_value = mock_table

        mock_insert = MagicMock()
        mock_table.insert.return_value = mock_insert
        mock_insert.execute.return_value = MagicMock(
            data=[{"id": order_id, "status": "pending", "total_price": 200000}]
        )

        order_data = {
            "full_name": "Test",
            "phone": "0901234567",
            "email": None,
            "pickup_date": datetime.now(timezone.utc) + timedelta(hours=25),
            "items": [
                {"product_id": uuid4(), "size": "20cm", "flavor": "chocolate",
                 "quantity": 1, "unit_price": 200000, "customization_json": None},
            ],
            "ai_summary": "Bánh kem chocolate 20cm, nhận ngày mai",
        }

        self.service.create_order(order_data, self.customer)

        # Verify ai_summary was included in the insert
        insert_call = mock_table.insert.call_args_list[0]
        inserted_data = insert_call[0][0]
        assert inserted_data["ai_summary"] == "Bánh kem chocolate 20cm, nhận ngày mai"

    def test_create_order_stores_customization_json(self):
        """Customization JSON should be stored in cake_customizations table."""
        order_id = str(uuid4())
        item_id = str(uuid4())

        mock_table = MagicMock()
        self.mock_supabase.table.return_value = mock_table

        mock_insert = MagicMock()
        mock_table.insert.return_value = mock_insert

        # First call returns order, second returns item, third returns customization, fourth returns history
        mock_insert.execute.side_effect = [
            MagicMock(data=[{"id": order_id, "status": "pending", "total_price": 200000}]),
            MagicMock(data=[{"id": item_id}]),
            MagicMock(data=[{"id": str(uuid4())}]),
            MagicMock(data=[{"id": str(uuid4())}]),
        ]

        customization = {
            "size": "20cm",
            "flavor": "chocolate",
            "cream_type": "whipped",
            "cream_color": "#FFFFFF",
            "zones": {"top": {"topping": "strawberry"}},
        }

        order_data = {
            "full_name": "Test",
            "phone": "0901234567",
            "email": None,
            "pickup_date": datetime.now(timezone.utc) + timedelta(hours=25),
            "items": [
                {"product_id": uuid4(), "size": "20cm", "flavor": "chocolate",
                 "quantity": 1, "unit_price": 200000,
                 "customization_json": customization},
            ],
            "ai_summary": None,
        }

        self.service.create_order(order_data, self.customer)

        # Verify cake_customizations insert was called
        # The third insert call should be for cake_customizations
        all_insert_calls = mock_table.insert.call_args_list
        # Find the customization insert (contains customization_json key)
        customization_calls = [
            call for call in all_insert_calls
            if "customization_json" in call[0][0]
        ]
        assert len(customization_calls) == 1
        assert customization_calls[0][0][0]["customization_json"] == customization
        assert customization_calls[0][0][0]["order_id"] == order_id
        assert customization_calls[0][0][0]["order_item_id"] == item_id


# ============================================================
# Order Service - Update Status Tests
# ============================================================


class TestUpdateOrderStatus:
    """Test order status update logic."""

    def setup_method(self):
        self.mock_supabase = MagicMock()
        self.service = OrderService(self.mock_supabase)

    def _setup_order_fetch(self, order_id, current_status):
        """Mock fetching an order with given status."""
        mock_table = MagicMock()
        self.mock_supabase.table.return_value = mock_table

        mock_select = MagicMock()
        mock_table.select.return_value = mock_select

        mock_eq1 = MagicMock()
        mock_select.eq.return_value = mock_eq1

        mock_single = MagicMock()
        mock_eq1.maybe_single.return_value = mock_single

        mock_single.execute.return_value = MagicMock(
            data={"id": order_id, "status": current_status, "customer_id": str(uuid4())}
        )

        # Also mock update chain
        mock_update = MagicMock()
        mock_table.update.return_value = mock_update
        mock_update_eq = MagicMock()
        mock_update.eq.return_value = mock_update_eq
        mock_update_eq.execute.return_value = MagicMock(
            data=[{"id": order_id, "status": "confirmed"}]
        )

        # Mock insert for history
        mock_insert = MagicMock()
        mock_table.insert.return_value = mock_insert
        mock_insert.execute.return_value = MagicMock(data=[{"id": str(uuid4())}])

        return mock_table

    def test_valid_transition_pending_to_confirmed_by_admin(self):
        """Admin can transition pending → confirmed."""
        order_id = str(uuid4())
        self._setup_order_fetch(order_id, "pending")

        admin = {"id": str(uuid4()), "role": "admin"}
        result = self.service.update_order_status(order_id, "confirmed", admin)
        assert result is not None

    def test_invalid_transition_pending_to_delivered(self):
        """Cannot skip statuses: pending → delivered is invalid."""
        order_id = str(uuid4())
        self._setup_order_fetch(order_id, "pending")

        admin = {"id": str(uuid4()), "role": "admin"}
        with pytest.raises(InvalidStatusTransitionError) as exc_info:
            self.service.update_order_status(order_id, "delivered", admin)
        assert "confirmed" in exc_info.value.message

    def test_invalid_transition_reverse_confirmed_to_pending(self):
        """Cannot reverse: confirmed → pending is invalid."""
        order_id = str(uuid4())
        self._setup_order_fetch(order_id, "confirmed")

        admin = {"id": str(uuid4()), "role": "admin"}
        with pytest.raises(InvalidStatusTransitionError) as exc_info:
            self.service.update_order_status(order_id, "pending", admin)
        assert "in_production" in exc_info.value.message

    def test_baker_cannot_confirm_order(self):
        """Baker cannot perform pending → confirmed (Admin only)."""
        order_id = str(uuid4())
        self._setup_order_fetch(order_id, "pending")

        baker = {"id": str(uuid4()), "role": "baker"}
        with pytest.raises(InsufficientPermissionError) as exc_info:
            self.service.update_order_status(order_id, "confirmed", baker)
        assert "baker" in exc_info.value.message

    def test_admin_cannot_start_production(self):
        """Admin cannot perform confirmed → in_production (Baker only)."""
        order_id = str(uuid4())
        self._setup_order_fetch(order_id, "confirmed")

        admin = {"id": str(uuid4()), "role": "admin"}
        with pytest.raises(InsufficientPermissionError) as exc_info:
            self.service.update_order_status(order_id, "in_production", admin)
        assert "admin" in exc_info.value.message

    def test_customer_cannot_update_status(self):
        """Customer cannot perform any status transition."""
        order_id = str(uuid4())
        self._setup_order_fetch(order_id, "pending")

        customer = {"id": str(uuid4()), "role": "customer"}
        with pytest.raises(InsufficientPermissionError):
            self.service.update_order_status(order_id, "confirmed", customer)

    def test_order_not_found_raises_error(self):
        """Non-existent order raises OrderNotFoundError."""
        order_id = str(uuid4())

        mock_table = MagicMock()
        self.mock_supabase.table.return_value = mock_table
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_single = MagicMock()
        mock_eq.maybe_single.return_value = mock_single
        mock_single.execute.return_value = MagicMock(data=None)

        admin = {"id": str(uuid4()), "role": "admin"}
        with pytest.raises(OrderNotFoundError):
            self.service.update_order_status(order_id, "confirmed", admin)


# ============================================================
# Schema Validation Tests
# ============================================================


class TestOrderSchemas:
    """Test Pydantic schema validation."""

    def test_create_order_request_valid(self):
        """Valid order request should pass validation."""
        data = {
            "full_name": "Nguyen Van A",
            "phone": "0901234567",
            "pickup_date": (datetime.now(timezone.utc) + timedelta(hours=25)).isoformat(),
            "items": [
                {
                    "product_id": str(uuid4()),
                    "size": "20cm",
                    "flavor": "chocolate",
                    "quantity": 1,
                    "unit_price": 200000,
                }
            ],
        }
        req = CreateOrderRequest(**data)
        assert req.full_name == "Nguyen Van A"
        assert req.phone == "0901234567"
        assert len(req.items) == 1

    def test_create_order_request_invalid_phone(self):
        """Phone with non-digits should fail."""
        data = {
            "full_name": "Test",
            "phone": "090-123-45",
            "pickup_date": (datetime.now(timezone.utc) + timedelta(hours=25)).isoformat(),
            "items": [
                {"product_id": str(uuid4()), "quantity": 1, "unit_price": 100000}
            ],
        }
        with pytest.raises(Exception):
            CreateOrderRequest(**data)

    def test_create_order_request_empty_items_rejected(self):
        """Order with no items should fail validation."""
        data = {
            "full_name": "Test",
            "phone": "0901234567",
            "pickup_date": (datetime.now(timezone.utc) + timedelta(hours=25)).isoformat(),
            "items": [],
        }
        with pytest.raises(Exception):
            CreateOrderRequest(**data)

    def test_create_order_request_empty_name_rejected(self):
        """Order with empty name should fail validation."""
        data = {
            "full_name": "",
            "phone": "0901234567",
            "pickup_date": (datetime.now(timezone.utc) + timedelta(hours=25)).isoformat(),
            "items": [
                {"product_id": str(uuid4()), "quantity": 1, "unit_price": 100000}
            ],
        }
        with pytest.raises(Exception):
            CreateOrderRequest(**data)

    def test_update_status_request_valid(self):
        """Valid status values should pass."""
        for status in ["pending", "confirmed", "in_production", "ready", "delivered"]:
            req = UpdateStatusRequest(status=status)
            assert req.status == status

    def test_update_status_request_invalid(self):
        """Invalid status value should fail."""
        with pytest.raises(Exception):
            UpdateStatusRequest(status="cancelled")

    def test_order_list_response_empty(self):
        """Empty order list should be valid."""
        data = {
            "orders": [],
            "pagination": {
                "page": 1,
                "page_size": 10,
                "total_items": 0,
                "total_pages": 0,
                "has_next": False,
                "has_previous": False,
            },
        }
        resp = OrderListResponse(**data)
        assert resp.orders == []
        assert resp.pagination.total_items == 0


# ============================================================
# Order Service - List Orders Tests
# ============================================================


class TestListCustomerOrders:
    """Test order listing logic."""

    def setup_method(self):
        self.mock_supabase = MagicMock()
        self.service = OrderService(self.mock_supabase)

    def test_list_orders_returns_pagination(self):
        """Should return correct pagination metadata."""
        customer_id = str(uuid4())

        mock_table = MagicMock()
        self.mock_supabase.table.return_value = mock_table

        # Mock count query
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_eq.execute.return_value = MagicMock(count=25)

        # Mock data query
        mock_order = MagicMock()
        mock_eq.order.return_value = mock_order
        mock_range = MagicMock()
        mock_order.range.return_value = mock_range
        mock_range.execute.return_value = MagicMock(data=[
            {"id": str(uuid4()), "status": "pending", "total_price": 200000,
             "pickup_date": "2024-01-15T10:00:00Z", "customer_name": "Test",
             "customer_phone": "0901234567", "created_at": "2024-01-10T10:00:00Z"}
        ])

        result = self.service.list_customer_orders(customer_id, page=1, page_size=10)

        assert result["pagination"]["total_items"] == 25
        assert result["pagination"]["total_pages"] == 3
        assert result["pagination"]["has_next"] is True
        assert result["pagination"]["has_previous"] is False


# ============================================================
# Error Classes Tests
# ============================================================


class TestErrorClasses:
    """Test custom error classes."""

    def test_order_not_found_error(self):
        err = OrderNotFoundError("abc-123")
        assert err.status_code == 404
        assert "abc-123" in err.message

    def test_invalid_status_transition_error(self):
        err = InvalidStatusTransitionError("pending", "delivered", ["confirmed"])
        assert err.status_code == 400
        assert "pending" in err.message
        assert "delivered" in err.message
        assert "confirmed" in err.message

    def test_insufficient_permission_error(self):
        err = InsufficientPermissionError("baker", "pending → confirmed")
        assert err.status_code == 403
        assert "baker" in err.message

    def test_pickup_date_validation_error(self):
        err = PickupDateValidationError("Too early")
        assert err.status_code == 400
        assert err.message == "Too early"
