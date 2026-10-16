"""Chạy trọn một đơn qua bốn vai trò, như tiệm thật.

Kịch bản: khách đặt → staff xác nhận → thợ sản xuất → sẵn sàng → staff bàn giao.

Vì sao cần riêng một file
-------------------------
`test_orders.py` kiểm từng bước một, mỗi bước dựng dữ liệu mới. Nó không bắt
được loại lỗi hay nhất: **các bước đúng riêng lẻ nhưng nối tiếp sai**. Ví dụ
thợ A nhận đơn, thợ B cũng sửa được; hoặc đơn bị giao hai lần nên cộng điểm
hai lần. Ở đây một đơn đi qua đủ chuỗi trên **cùng một ID**, giữ đúng người
ở mỗi bước, và kiểm cả những đường bị bỏ qua.

Cách dựng CSDL giả
------------------
`FakeOrderDb` giữ trạng thái đơn trong bộ nhớ và ghi lại mọi lệnh ghi, nên test
kiểm được "cột nào thực sự bị đổi" chứ không chỉ "hàm không ném lỗi". Đây là
điểm khác biệt so với `MagicMock` trả sẵn một giá trị: mock không phản ánh
đơn có thực sự đi từ `pending` sang `confirmed` hay không.
"""

from __future__ import annotations

import pytest

from app.services.order_service import (
    InsufficientPermissionError,
    InvalidStatusTransitionError,
    OrderService,
)


CUSTOMER = {"id": "khach-1", "role": "customer"}
STAFF_A = {"id": "nhan-vien-1", "role": "staff"}
STAFF_B = {"id": "nhan-vien-2", "role": "staff"}
BAKER_A = {"id": "tho-1", "role": "baker"}
BAKER_B = {"id": "tho-2", "role": "baker"}
ADMIN = {"id": "quan-ly", "role": "admin"}


class _Res:
    """Kết quả trả về giống `MagicMock(data=...)` mà supabase-py dùng."""

    def __init__(self, data):
        self.data = data


class FakeOrderDb:
    """CSDL giả giữ trạng thái thật của một đơn, và ghi lại mọi lệnh ghi."""

    def __init__(self, order: dict | None = None):
        self.order = order or {
            "id": "don-1",
            "status": "draft",
            "customer_id": CUSTOMER["id"],
            "total_price": 480_000,
        }
        self.updates: list[dict] = []
        self.history: list[dict] = []
        self.baker_history: list[dict] = []

    def table(self, name: str):
        db = self

        class _Table:
            # Cờ nằm trên CHUỖI LỆNH, không nằm trên db. Nếu đặt ở db thì sau
            # lần `update` đầu tiên nó giữ nguyên True, và mọi `select` sau đó
            # cũng trả về list — service lỗi `TypeError: list indices must be
            # integers`. Mỗi lần gọi `table()` là một chuỗi lệnh mới.
            def __init__(self):
                self.is_write = False
                self.limit_one = False

            def select(self, *a, **k):
                return self

            def eq(self, *a, **k):
                return self

            def maybe_single(self):
                return self

            def order(self, *a, **k):
                return self

            def limit(self, *a, **k):
                self.limit_one = True
                return self

            def in_(self, *a, **k):
                return self

            def execute(self):
                # Truy vấn của `_check_baker_authorization` lọc
                # `new_status = 'in_production'` rồi `limit(1)`, nên fake cũng
                # phải lọc và lấy dòng MỚI NHẤT. Trả về toàn bộ lịch sử sẽ
                # khiến test "thợ B không sửa được đơn của thợ A" xanh vì lý do
                # sai — dòng đầu tiên có thể là của chính B.
                if name == "order_status_history":
                    claimed = [
                        row for row in db.baker_history
                        if row.get("new_status") == "in_production"
                    ]
                    return _Res(claimed[-1:] if self.limit_one else list(claimed))
                # supabase-py trả list cho lệnh ghi, dict cho lệnh đọc.
                if self.is_write:
                    return _Res([dict(db.order)])
                return _Res(dict(db.order))

            def update(self, payload: dict):
                db.updates.append(payload)
                self.is_write = True
                db.order.update(payload)
                return self

            def insert(self, payload: dict):
                if name == "order_status_history":
                    db.history.append(payload)
                    db.baker_history.append(payload)
                return self

        return _Table()


# `LoyaltyService` được import bên trong hàm, nên phải chặn ở đó. Không chặn
# thì test gọi thật vào Supabase — chậm, và tạo dữ liệu rác trong CSDL của tiệm.
@pytest.fixture(autouse=True)
def _no_loyalty_calls(monkeypatch):
    import app.services.loyalty_service as loyalty_mod

    def _boom(self, *a, **k):
        raise AssertionError("Không nên gọi LoyaltyService trong các test này")

    monkeypatch.setattr(loyalty_mod.LoyaltyService, "award_points", _boom, raising=False)


def _service(order_status: str = "draft") -> tuple[OrderService, FakeOrderDb]:
    db = FakeOrderDb(
        {
            "id": "don-1",
            "status": order_status,
            "customer_id": CUSTOMER["id"],
            "total_price": 480_000,
        }
    )
    return OrderService(db), db


class TestHappyPathAcrossFourRoles:
    """Đủ chuỗi, mỗi bước đúng người."""

    def test_order_travels_from_draft_to_delivered(self):
        service, db = _service("draft")

        steps = [
            ("pending", STAFF_A),      # nhân viên nhận đơn nháp
            ("confirmed", STAFF_A),    # nhân viên xác nhận
            ("in_production", BAKER_A),  # thợ bắt tay làm
            ("ready", BAKER_A),        # thợ làm xong
            ("delivered", STAFF_A),    # nhân viên bàn giao
        ]
        for target, actor in steps:
            service.update_order_status("don-1", target, actor)

        assert db.order["status"] == "delivered"

    def test_every_step_is_recorded_in_history_with_the_right_actor(self):
        service, db = _service("draft")

        for target, actor in [
            ("pending", STAFF_A),
            ("confirmed", STAFF_A),
            ("in_production", BAKER_A),
            ("ready", BAKER_A),
            ("delivered", STAFF_A),
        ]:
            service.update_order_status("don-1", target, actor)

        assert [h["new_status"] for h in db.history] == [
            "pending", "confirmed", "in_production", "ready", "delivered",
        ]
        assert [h["changed_by"] for h in db.history] == [
            STAFF_A["id"], STAFF_A["id"], BAKER_A["id"], BAKER_A["id"], STAFF_A["id"],
        ]

    def test_each_step_writes_only_the_status_and_timestamp(self):
        """Không được lễ hội ghi đè cột khác — tổng tiền là của khách, không
        được tính lại giữa chừng."""
        service, db = _service("draft")

        service.update_order_status("don-1", "pending", STAFF_A)

        assert db.updates == [{"status": "pending", "updated_at": db.updates[0]["updated_at"]}]
        assert set(db.updates[0]) == {"status", "updated_at"}


class TestNoStepCanBeSkipped:
    """Đi từng bước một, cố nhảy bước phải bị chặn."""

    def test_draft_cannot_jump_to_confirmed(self):
        service, _ = _service("draft")
        with pytest.raises(InvalidStatusTransitionError):
            service.update_order_status("don-1", "confirmed", STAFF_A)

    def test_pending_cannot_jump_to_in_production(self):
        service, _ = _service("pending")
        with pytest.raises(InvalidStatusTransitionError):
            service.update_order_status("don-1", "in_production", BAKER_A)

    def test_confirmed_cannot_jump_to_ready(self):
        service, _ = _service("confirmed")
        with pytest.raises(InvalidStatusTransitionError):
            service.update_order_status("don-1", "ready", BAKER_A)

    def test_ready_cannot_go_back_to_in_production(self):
        service, _ = _service("ready")
        with pytest.raises(InvalidStatusTransitionError):
            service.update_order_status("don-1", "in_production", BAKER_A)

    def test_delivered_is_final(self):
        service, _ = _service("delivered")
        with pytest.raises(InvalidStatusTransitionError):
            service.update_order_status("don-1", "ready", STAFF_A)


class TestWrongRoleIsBlockedAtEveryStep:
    """Đúng là đi sai người ở bước nào cũng phải bị chặn."""

    @pytest.mark.parametrize(
        "status,target,blocked_role",
        [
            ("draft", "pending", "baker"),
            ("draft", "pending", "customer"),
            ("pending", "confirmed", "baker"),
            ("pending", "confirmed", "customer"),
            ("confirmed", "in_production", "staff"),
            ("confirmed", "in_production", "customer"),
            ("in_production", "ready", "staff"),
            ("in_production", "ready", "customer"),
            ("ready", "delivered", "baker"),
            ("ready", "delivered", "customer"),
        ],
    )
    def test_role_cannot_perform_transition(self, status, target, blocked_role):
        service, db = _service(status)

        with pytest.raises(InsufficientPermissionError):
            service.update_order_status("don-1", target, {"id": "x", "role": blocked_role})

        # Quan trọng: đơn phải giữ nguyên, không phải "chặn sau khi đã đổi".
        assert db.order["status"] == status
        assert db.updates == []

    @pytest.mark.parametrize("status", ["draft", "pending", "confirmed", "in_production", "ready"])
    def test_admin_cannot_stand_in_for_operations(self, status):
        """Admin không nằm trong bất kỳ bước nào của `VALID_TRANSITIONS`.

        Dễ hiểu nhầm là admin có mọi quyền. Thực tế admin đọc qua
        `/admin/orders`, còn việc bán và làm bánh thuộc staff và thợ.
        """
        service, _ = _service(status)
        nxt = {
            "draft": "pending",
            "pending": "confirmed",
            "confirmed": "in_production",
            "in_production": "ready",
            "ready": "delivered",
        }[status]

        with pytest.raises(InsufficientPermissionError):
            service.update_order_status("don-1", nxt, ADMIN)


class TestOnlyTheClaimingBakerCanContinue:
    """Sau khi thợ nhận đơn, thợ khác không sửa được."""

    def test_second_baker_cannot_finish_another_bakers_order(self):
        service, db = _service("confirmed")
        service.update_order_status("don-1", "in_production", BAKER_A)

        # BAKER_B có vai trò đúng, đơn cũng không thuộc chi nhánh nào khác,
        # nên chỉ có thể bị chặn bởi luật "thợ đã nhận".
        with pytest.raises(InsufficientPermissionError):
            service.update_order_status("don-1", "ready", BAKER_B)

        assert db.order["status"] == "in_production"

    def test_claiming_baker_can_finish(self):
        service, db = _service("confirmed")
        service.update_order_status("don-1", "in_production", BAKER_A)

        service.update_order_status("don-1", "ready", BAKER_A)

        assert db.order["status"] == "ready"

    def test_unclaimed_order_is_open_to_any_baker(self):
        """Đơn `confirmed` chưa ai nhận: thợ nào cũng lấy được, không giành nhau."""
        service, _ = _service("confirmed")

        service.update_order_status("don-1", "in_production", BAKER_B)

    def test_baker_claiming_does_not_block_staff_from_delivering(self):
        """Luật của thợ không được áp vào bước của nhân viên."""
        service, db = _service("confirmed")
        service.update_order_status("don-1", "in_production", BAKER_A)
        service.update_order_status("don-1", "ready", BAKER_A)

        # Nhân viên khác vẫn bàn giao được, dù không phải thợ đã làm.
        service.update_order_status("don-1", "delivered", STAFF_B)

        assert db.order["status"] == "delivered"


class TestLoyaltyPointsOnDelivery:
    """Giao xong mới cộng điểm, và cộng một lần."""

    def test_points_awarded_once_on_delivery(self, monkeypatch):
        import app.core.dependencies as deps
        import app.services.loyalty_service as loyalty_mod

        service, db = _service("ready")
        awarded: list[dict] = []

        def _award(self, user_id, amount_vnd, source_type, ref_id):
            awarded.append(
                {"user_id": user_id, "amount_vnd": amount_vnd, "ref_id": ref_id}
            )

        monkeypatch.setattr(loyalty_mod.LoyaltyService, "award_points", _award)
        monkeypatch.setattr(deps, "get_supabase_client", lambda *a, **k: object())

        service.update_order_status("don-1", "delivered", STAFF_A)

        assert awarded == [
            {"user_id": CUSTOMER["id"], "amount_vnd": 480_000, "ref_id": "don-1"}
        ]

    def test_no_points_before_delivery(self, monkeypatch):
        import app.core.dependencies as deps
        import app.services.loyalty_service as loyalty_mod

        service, _ = _service("draft")
        awarded: list[dict] = []

        monkeypatch.setattr(
            loyalty_mod.LoyaltyService, "award_points",
            lambda self, **k: awarded.append(k),
        )
        monkeypatch.setattr(deps, "get_supabase_client", lambda *a, **k: object())

        for target, actor in [
            ("pending", STAFF_A),
            ("confirmed", STAFF_A),
            ("in_production", BAKER_A),
            ("ready", BAKER_A),
        ]:
            service.update_order_status("don-1", target, actor)

        assert awarded == [], "Chưa giao mà đã cộng điểm."

    def test_a_failed_award_does_not_fail_the_delivery(self, monkeypatch):
        """Điểm là phần thưởng, không phải điều kiện để giao hàng.

        Nếu bảng điểm lỗi mà khách không nhận được bánh thì thiệt hơn là ngược lại.
        """
        import app.core.dependencies as deps
        import app.services.loyalty_service as loyalty_mod

        service, db = _service("ready")

        def _raise(self, **k):
            raise RuntimeError("bảng loyalty hỏng")

        monkeypatch.setattr(loyalty_mod.LoyaltyService, "award_points", _raise)
        monkeypatch.setattr(deps, "get_supabase_client", lambda *a, **k: object())

        result = service.update_order_status("don-1", "delivered", STAFF_A)

        assert result["status"] == "delivered"
        assert db.order["status"] == "delivered"
