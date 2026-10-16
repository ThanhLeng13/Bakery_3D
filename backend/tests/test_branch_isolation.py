"""Ranh giới chi nhánh của thợ — và chỗ code đang tưởng có nhưng không có.

Kết quả đo trên CSDL thật (16/10): bảng `orders`, `users` và `order_items`
**đều không có cột `branch_id`**. Xác nhận bằng cách `select *` rồi đọc khoá cột,
và bằng câu hỏi trực tiếp cho PostgREST — cả hai đều trả lỗi `42703`.

Hệ quả cụ thể:

`_check_baker_authorization` có nhánh "kiểm tra chi nhánh":

    baker_branch = baker.get("branch_id") or ...user_metadata...branch_id
    order_branch = order.get("branch_id")
    if baker_branch and order_branch and baker_branch != order_branch:
        raise InsufficientPermissionError(...)

Nhánh này **không bao giờ chạy**, vì cả hai vế đều luôn là `None`. Không phải vì
sai logic — mà vì không có dữ liệu để kiểm tra. Test dưới đây khoá lại đúng hành
vi đang có, để khi ai đó thêm cột thì test đỏ và buộc phải nghĩ xem có cần lọc
theo chi nhánh không.

Phần bảo vệ **đang có hiệu lực** là phần thứ hai của cùng hàm: thợ chỉ sửa được
đơn mình đã nhận, xét qua `order_status_history.changed_by`. Test dưới đây kiểm
cả hai phần, và nói rõ phần nào đang chạy và phần nào không.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.services.order_service import (
    InsufficientPermissionError,
    OrderService,
)


ORDER_ID = "11111111-1111-1111-1111-111111111111"
BAKER_A = {"id": "baker-a", "role": "baker"}
BAKER_B = {"id": "baker-b", "role": "baker"}


def _service(order: dict, history_rows: list[dict] | None = None) -> OrderService:
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
        data=order
    )
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
        data=history_rows or []
    )
    return OrderService(db)


class TestBranchIsolationIsCurrentlyInert:
    """Chi nhánh không lọc được, vì cột không tồn tại. Ghi lại đúng như vậy."""

    def test_branch_mismatch_is_not_blocked_today(self):
        """Hai thợ khác chi nhánh vẫn thấy nhau — vì không có dữ liệu chi nhánh.

        Test này KHÔNG khẳng định đây là điều mong muốn. Nó ghi lại hành vi hiện
        tại để không ai tưởng đã có chốt chi nhánh.

        Cần nói rõ: thêm cột `branch_id` vào CSDL sẽ **không** làm test này đỏ.
        Ở đây `order` là dict dựng trong test, không đọc từ CSDL, nên nó sẽ vẫn
        không có khoá `branch_id` và nhánh kiểm tra vẫn không chạy. Muốn chặt được
        thì phải là một ca khác — `TestBranchIsolationWouldWorkWithData` bên dưới,
        truyền `branch_id` vào thật.
        """
        order = {"id": ORDER_ID, "status": "in_production", "customer_id": "c1"}

        # Thợ B khác chi nhánh A: nếu có dữ liệu, nhánh 1 sẽ chặn.
        service = _service(order, history_rows=[{"changed_by": BAKER_A["id"]}])

        with pytest.raises(InsufficientPermissionError):
            # Bị chặn bởi nhánh 2 (đơn do BAKER_A nhận), KHÔNG phải nhánh 1.
            service._check_baker_authorization(ORDER_ID, order, BAKER_B)

    def test_branch_filter_cannot_trigger_without_the_column(self):
        """Cùng tình huống nhưng đơn chưa ai nhận: không có gì chặn.

        Không có `branch_id` ở bất kỳ đâu nên `baker_branch` và `order_branch`
        đều `None`, điều kiện `if baker_branch and order_branch` không bao giờ
        đúng. Thợ B mở được đơn của thợ A khi đơn còn ở `confirmed`.
        """
        order = {"id": ORDER_ID, "status": "confirmed", "customer_id": "c1"}
        service = _service(order, history_rows=[])

        # Không ném ra: tức nhánh chi nhánh không chạy.
        service._check_baker_authorization(ORDER_ID, order, BAKER_B, read_only=True)


class TestBranchIsolationWouldWorkWithData:
    """Logic nhánh chi nhánh ĐÚNG — chỉ là chưa có dữ liệu để chạy.

    Khác với lớp trên: ở đây `branch_id` được truyền vào thật. Nếu nhánh kiểm tra
    viết sai (ví dụ so sánh sai biến, hoặc dùng `==` chỗ phải `!=`) thì lớp này
    đỏ, còn lớp trên vẫn xanh — nên cần cả hai.
    """

    def test_baker_from_another_branch_is_blocked(self):
        order = {
            "id": ORDER_ID,
            "status": "in_production",
            "customer_id": "c1",
            "branch_id": "chi-nhanh-ha-noi",
        }
        baker = {"id": "baker-c", "role": "baker", "branch_id": "chi-nhanh-da-nang"}
        service = _service(order, history_rows=[])

        with pytest.raises(InsufficientPermissionError):
            service._check_baker_authorization(ORDER_ID, order, baker)

    def test_baker_from_same_branch_passes(self):
        order = {
            "id": ORDER_ID,
            "status": "in_production",
            "customer_id": "c1",
            "branch_id": "chi-nhanh-da-nang",
        }
        baker = {"id": "baker-c", "role": "baker", "branch_id": "chi-nhanh-da-nang"}
        service = _service(order, history_rows=[{"changed_by": baker["id"]}])

        service._check_baker_authorization(ORDER_ID, order, baker)

    def test_branch_from_user_metadata_is_also_read(self):
        """`branch_id` có thể nằm trong metadata; cả hai đều phải được đọc."""
        order = {
            "id": ORDER_ID,
            "status": "in_production",
            "customer_id": "c1",
            "branch_id": "chi-nhanh-ha-noi",
        }
        baker = {
            "id": "baker-c",
            "role": "baker",
            "user_metadata": {"branch_id": "chi-nhanh-da-nang"},
        }
        service = _service(order, history_rows=[])

        with pytest.raises(InsufficientPermissionError):
            service._check_baker_authorization(ORDER_ID, order, baker)


class TestBakerOwnershipIsEnforced:
    """Phần bảo vệ ĐANG chạy: thợ không sửa được đơn thợ khác đã nhận."""

    def test_other_baker_cannot_modify_claimed_order(self):
        order = {"id": ORDER_ID, "status": "in_production", "customer_id": "c1"}
        service = _service(order, history_rows=[{"changed_by": BAKER_A["id"]}])

        with pytest.raises(InsufficientPermissionError):
            service._check_baker_authorization(ORDER_ID, order, BAKER_B)

    def test_claiming_baker_can_continue(self):
        order = {"id": ORDER_ID, "status": "in_production", "customer_id": "c1"}
        service = _service(order, history_rows=[{"changed_by": BAKER_A["id"]}])

        service._check_baker_authorization(ORDER_ID, order, BAKER_A)

    def test_read_only_ignores_ownership(self):
        """Đọc thì ai cũng được trong khu vực thợ — cần xem để rà việc."""
        order = {"id": ORDER_ID, "status": "in_production", "customer_id": "c1"}
        service = _service(order, history_rows=[{"changed_by": BAKER_A["id"]}])

        service._check_baker_authorization(ORDER_ID, order, BAKER_B, read_only=True)

    def test_unclaimed_order_is_open_to_any_baker(self):
        """Đơn `confirmed` chưa ai nhận: thợ nào cũng lấy được.

        Đây là chủ ý — không có nhánh nào ghi "tôi sẽ làm", nên chưa có chủ. Khi
        chuyển `confirmed → in_production` thì `changed_by` mới ghi lại.
        """
        order = {"id": ORDER_ID, "status": "confirmed", "customer_id": "c1"}
        service = _service(order, history_rows=[])

        service._check_baker_authorization(ORDER_ID, order, BAKER_B)


class TestNonBakerSkipsTheCheck:
    """`if baker.get("role") != "baker": return` — staff/admin không bị chặn."""

    @pytest.mark.parametrize("role", ("staff", "admin", "customer"))
    def test_other_roles_pass_through(self, role):
        order = {"id": ORDER_ID, "status": "in_production", "customer_id": "c1"}
        service = _service(order, history_rows=[{"changed_by": BAKER_A["id"]}])

        service._check_baker_authorization(
            ORDER_ID, order, {"id": "someone", "role": role}
        )
