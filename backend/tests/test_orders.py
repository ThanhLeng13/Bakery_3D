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
from app.services.pricing import NIL_UUID


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

    def test_pending_to_confirmed_requires_staff(self):
        assert get_allowed_roles_for_transition("pending", "confirmed") == ["staff"]

    def test_confirmed_to_in_production_requires_baker(self):
        assert get_allowed_roles_for_transition("confirmed", "in_production") == ["baker"]

    def test_in_production_to_ready_requires_baker(self):
        assert get_allowed_roles_for_transition("in_production", "ready") == ["baker"]

    def test_ready_to_delivered_requires_staff(self):
        assert get_allowed_roles_for_transition("ready", "delivered") == ["staff"]

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

    def test_null_size_does_not_crash(self):
        """size may be null or absent: item.get("size", "") returned None when
        the key existed with a null value, and None.lower() raised
        AttributeError -> HTTP 500."""
        pickup = datetime.now(timezone.utc) + timedelta(hours=72)

        # None of these may raise
        self.service._validate_pickup_date(pickup, [{"size": None}])
        self.service._validate_pickup_date(pickup, [{}])
        # Whitespace/case variants still count as two-tier (needs 72h here).
        self.service._validate_pickup_date(pickup, [{"size": " 2-Tier "}])


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

    def _rpc_args(self, name="rpc_create_order"):
        """Tham số truyền cho RPC, theo tên.

        Đơn được ghi trong MỘT lệnh `rpc_create_order` để Postgres hoặc ghi hết,
        hoặc không ghi gì — tránh đơn lưu dở. Test cũ đọc `table().insert()`
        không còn đúng, nên dùng helper này.
        """
        calls = self.mock_supabase.rpc.call_args_list
        for call in calls:
            if call[0][0] == name:
                return call[0][1]
        raise AssertionError(f"không có lệnh RPC '{name}' trong số lệnh đã gọi")

    def _mock_rpc_result(self, total=0, duplicate=False):
        """Cho `supabase.rpc(...)` trả về một đơn đã tạo."""
        self.mock_supabase.rpc.return_value.execute.return_value = MagicMock(
            data=[{
                "order_id": str(uuid4()),
                "subtotal": total,
                "discount": 0,
                "total": total,
                "duplicate": duplicate,
            }]
        )
    def test_create_order_calculates_total_price_from_server_prices(self):
        """Total price comes from the server size table, never the client value."""
        order_id = str(uuid4())

        mock_table = MagicMock()
        self.mock_supabase.table.return_value = mock_table

        mock_insert = MagicMock()
        mock_table.insert.return_value = mock_insert
        mock_insert.execute.side_effect = [
            MagicMock(data=[{"id": order_id, "status": "pending"}]),
            MagicMock(data=[{"id": str(uuid4())}]),
            MagicMock(data=[{"id": str(uuid4())}]),
            MagicMock(data=[{"id": str(uuid4())}]),
        ]

        order_data = {
            "full_name": "Test",
            "phone": "0901234567",
            "email": None,
            "pickup_date": datetime.now(timezone.utc) + timedelta(hours=25),
            "items": [
                # Custom cakes carry the nil product id. The client claims 1 VND
                # and 999 VND; both must be ignored.
                {"product_id": NIL_UUID, "size": "20cm", "flavor": "chocolate",
                 "quantity": 2, "unit_price": 1, "customization_json": None},
                {"product_id": NIL_UUID, "size": "16cm", "flavor": "vanilla",
                 "quantity": 1, "unit_price": 999, "customization_json": None},
            ],
            "ai_summary": None,
        }

        self.service.create_order(order_data, self.customer)

        args = self._rpc_args()
        assert args["p_total_price"] == 950000  # 350000*2 + 250000*1

    # ── Voucher ──────────────────────────────────────────────────────────
    #
    # Khách đổi điểm được mã giảm 5.000đ; trước đây không nơi nào đọc mã đó.
    # Các test khoá lại: mức giảm lấy từ bảng vouchers, không lấy từ client,
    # và mã bị đánh dấu đã dùng sau khi đơn ghi xong.

    def _voucher_query(self, row):
        """Giả lập `table("vouchers").select(...).eq(...).limit(1).execute()`."""
        mock_select = MagicMock()
        mock_eq = MagicMock()
        mock_limit = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_eq.limit.return_value = mock_limit
        mock_limit.execute.return_value = MagicMock(data=[row] if row else [])
        return mock_select

    def test_voucher_hop_le_giam_tien_va_ghi_vao_don(self):
        order_id = str(uuid4())
        mock_table = MagicMock()
        self.mock_supabase.table.return_value = mock_table
        mock_insert = MagicMock()
        mock_table.insert.return_value = mock_insert
        mock_insert.execute.side_effect = [
            MagicMock(data=[{"id": order_id, "status": "pending"}]),
            *[MagicMock(data=[{"id": str(uuid4())}]) for _ in range(6)],
        ]
        voucher = {
            "id": "v-1",
            "code": "BNB-ABCD1234",
            "user_id": self.customer["id"],
            "discount_vnd": 5000,
            "status": "active",
            "expires_at": None,
            "used_at": None,
        }
        mock_table.select.return_value = self._voucher_query(voucher)

        order_data = {
            "full_name": "Test",
            "phone": "0901234567",
            "email": None,
            "pickup_date": datetime.now(timezone.utc) + timedelta(hours=25),
            "items": [
                {"product_id": NIL_UUID, "size": "20cm", "flavor": None,
                 "quantity": 1, "unit_price": 1, "customization_json": None},
            ],
            "ai_summary": None,
            "voucher_code": "BNB-ABCD1234",
        }

        result = self.service.create_order(order_data, self.customer)

        args = self._rpc_args()
        assert args["p_total_price"] == 350000 - 5000
        assert args["p_voucher_code"] == "BNB-ABCD1234"
        assert args["p_voucher_discount"] == 5000
        assert result["discount"] == 5000
        assert result["subtotal"] == 350000

    def test_don_khong_voucher_thi_ghi_ma_null(self):
        order_id = str(uuid4())
        mock_table = MagicMock()
        self.mock_supabase.table.return_value = mock_table
        mock_insert = MagicMock()
        mock_table.insert.return_value = mock_insert
        mock_insert.execute.side_effect = [
            MagicMock(data=[{"id": order_id, "status": "pending"}]),
            *[MagicMock(data=[{"id": str(uuid4())}]) for _ in range(6)],
        ]
        order_data = {
            "full_name": "Test",
            "phone": "0901234567",
            "email": None,
            "pickup_date": datetime.now(timezone.utc) + timedelta(hours=25),
            "items": [
                {"product_id": NIL_UUID, "size": "20cm", "flavor": None,
                 "quantity": 1, "unit_price": 1, "customization_json": None},
            ],
            "ai_summary": None,
        }
        self.service.create_order(order_data, self.customer)
        args = self._rpc_args()
        assert args["p_total_price"] == 350000
        assert args["p_voucher_code"] is None
        assert args["p_voucher_discount"] == 0

    def test_voucher_cua_khach_khac_bi_tu_choi(self):
        mock_table = MagicMock()
        self.mock_supabase.table.return_value = mock_table
        # Không có dòng nào khớp: mã không thuộc khách này.
        mock_table.select.return_value = self._voucher_query(None)

        order_data = {
            "full_name": "Test",
            "phone": "0901234567",
            "email": None,
            "pickup_date": datetime.now(timezone.utc) + timedelta(hours=25),
            "items": [
                {"product_id": NIL_UUID, "size": "20cm", "flavor": None,
                 "quantity": 1, "unit_price": 1, "customization_json": None},
            ],
            "ai_summary": None,
            "voucher_code": "BNB-KHACNGUOI",
        }
        with pytest.raises(OrderServiceError) as exc:
            self.service.create_order(order_data, self.customer)
        assert exc.value.status_code == 400
    def test_order_item_rows_store_the_server_price(self):
        """order_items.unit_price must hold the resolved price, not the client's."""
        order_id = str(uuid4())

        mock_table = MagicMock()
        self.mock_supabase.table.return_value = mock_table

        mock_insert = MagicMock()
        mock_table.insert.return_value = mock_insert
        mock_insert.execute.side_effect = [
            MagicMock(data=[{"id": order_id, "status": "pending"}]),
            MagicMock(data=[{"id": str(uuid4())}]),
            MagicMock(data=[{"id": str(uuid4())}]),
        ]

        order_data = {
            "full_name": "Test",
            "phone": "0901234567",
            "email": None,
            # Two-tier cakes need 48h notice, so book far enough ahead.
            "pickup_date": datetime.now(timezone.utc) + timedelta(hours=72),
            "items": [
                {"product_id": NIL_UUID, "size": "2-tier", "flavor": "chocolate",
                 "quantity": 1, "unit_price": 1000, "customization_json": None},
            ],
            "ai_summary": None,
        }

        self.service.create_order(order_data, self.customer)

        items = self._rpc_args()["p_items"]
        assert len(items) == 1
        assert items[0]["unit_price"] == 650000

    def test_custom_cake_price_read_from_customization_size(self):
        """The saved design's size wins over the loose item size field."""
        prices = self.service._resolve_unit_prices([
            {
                "product_id": NIL_UUID,
                "size": None,
                "quantity": 1,
                "unit_price": 1000,
                "customization_json": {"size": "24cm"},
            }
        ])
        assert prices == [450000]

    def test_catalogue_product_uses_base_price(self):
        """A real product is priced from products.base_price."""
        mock_table = MagicMock()
        self.mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"base_price": 275000}
        )

        prices = self.service._resolve_unit_prices([
            {"product_id": str(uuid4()), "quantity": 1, "unit_price": 1000}
        ])
        assert prices == [275000]

    def test_unknown_product_is_rejected(self):
        """A product id absent from the catalogue must not silently price at 0."""
        mock_table = MagicMock()
        self.mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data=None
        )

        with pytest.raises(OrderServiceError) as exc_info:
            self.service._resolve_unit_prices([
                {"product_id": str(uuid4()), "quantity": 1, "unit_price": 1000}
            ])
        assert exc_info.value.status_code == 400

    def test_create_order_stores_ai_summary(self):
        """AI summary should be stored in the order record."""
        order_id = str(uuid4())

        mock_table = MagicMock()
        self.mock_supabase.table.return_value = mock_table

        self._mock_rpc_result(total=350000)

        order_data = {
            "full_name": "Test",
            "phone": "0901234567",
            "email": None,
            "pickup_date": datetime.now(timezone.utc) + timedelta(hours=25),
            "items": [
                {"product_id": NIL_UUID, "size": "20cm", "flavor": "chocolate",
                 "quantity": 1, "unit_price": 200000, "customization_json": None},
            ],
            "ai_summary": "Bánh kem chocolate 20cm, nhận ngày mai",
        }

        self.service.create_order(order_data, self.customer)

        assert self._rpc_args()["p_ai_summary"] == (
            "Bánh kem chocolate 20cm, nhận ngày mai"
        )

    def test_create_order_stores_customization_json(self):
        """Customization JSON should be stored in cake_customizations table."""
        order_id = str(uuid4())
        item_id = str(uuid4())

        mock_table = MagicMock()
        self.mock_supabase.table.return_value = mock_table

        mock_insert = MagicMock()
        mock_table.insert.return_value = mock_insert
        self._mock_rpc_result(total=350000)

        # (không còn insert tay: rpc_create_order ghi mọi bảng trong 1 lệnh)
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
                {"product_id": NIL_UUID, "size": "20cm", "flavor": "chocolate",
                 "quantity": 1, "unit_price": 200000,
                 "customization_json": customization},
            ],
            "ai_summary": None,
        }

        self.service.create_order(order_data, self.customer)

        # Cấu hình bánh đi kèm từng món; `rpc_create_order` ghi vào
        # `cake_customizations` trong cùng transaction.
        items = self._rpc_args()["p_items"]
        assert len(items) == 1
        assert items[0]["customization_json"] == customization
        # Món tùy chỉnh không có dòng sản phẩm danh mục: product_id rỗng để
        # Postgres ghi NULL, tránh vi phạm khoá ngoại.
        assert items[0]["product_id"] == ""


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

    def test_valid_transition_pending_to_confirmed_by_staff(self):
        """Sales staff can transition pending → confirmed."""
        order_id = str(uuid4())
        self._setup_order_fetch(order_id, "pending")

        staff = {"id": str(uuid4()), "role": "staff"}
        result = self.service.update_order_status(order_id, "confirmed", staff)
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
        """Baker cannot perform pending → confirmed (Staff only)."""
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

    def test_admin_cannot_confirm_order(self):
        """Managers observe orders but sales staff own customer hand-off steps."""
        order_id = str(uuid4())
        self._setup_order_fetch(order_id, "pending")

        admin = {"id": str(uuid4()), "role": "admin"}
        with pytest.raises(InsufficientPermissionError):
            self.service.update_order_status(order_id, "confirmed", admin)

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
