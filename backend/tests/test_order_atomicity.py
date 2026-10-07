"""Đơn không được lưu dở, và gửi lại không được tạo đơn thứ hai.

Bối cảnh
--------
`create_order` ghi nhiều bảng qua nhiều lệnh riêng: `orders`, rồi `order_items`
cho từng món, rồi `cake_customizations`, rồi `order_status_history`, rồi đánh
dấu voucher đã dùng. Không gói nào bao trọn: nếu lệnh thứ ba hỏng, bảng
`orders` đã có dòng và `order_items` đã có hai dòng — đơn nằm trong CSDL thiếu
món, tổng tiền không khớp số tiền thực, và thợ nhận việc không làm được.

Khách cũng dễ bấm "Đặt hàng" hai lần khi mạng chập chờn, mỗi lần một đơn.

Cách sửa: ghi mọi thứ trong một lệnh duy nhất qua RPC `rpc_create_order` để
Postgres hoặc ghi hết, hoặc không ghi gì; kèm khoá idempotency để lần gửi lại
trả về đơn cũ.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.services.order_service import OrderService, OrderServiceError
from app.services.pricing import NIL_UUID


def _order_data(**over):
    base = {
        "full_name": "Test",
        "phone": "0901234567",
        "email": None,
        "pickup_date": datetime.now(timezone.utc) + timedelta(hours=48),
        "items": [
            {"product_id": NIL_UUID, "size": "20cm", "flavor": None,
             "quantity": 1, "unit_price": 1, "customization_json": None},
            {"product_id": NIL_UUID, "size": "16cm", "flavor": None,
             "quantity": 1, "unit_price": 1, "customization_json": None},
        ],
        "ai_summary": None,
    }
    base.update(over)
    return base


class _TableStub:
    """Ghi lại thao tác, cho phép ép lỗi ở một bảng bất kỳ."""

    def __init__(self, name, calls, fail_on=None):
        self.name = name
        self.calls = calls
        self.fail_on = fail_on

    def _maybe_fail(self):
        if self.name == self.fail_on:
            raise RuntimeError(f"lỗi giả lập khi ghi {self.name}")

    def insert(self, payload):
        self._maybe_fail()
        self.calls.append(("insert", self.name, payload))
        return self

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        self._maybe_fail()
        if self.name == "orders":
            return MagicMock(data=[{"id": "o-1", "status": "pending"}])
        return MagicMock(data=[{"id": f"{self.name}-1"}])


class _ClientStub:
    def __init__(self, fail_on=None):
        self.calls = []
        self.fail_on = fail_on

    def table(self, name):
        return _TableStub(name, self.calls, self.fail_on)

    def rpc(self, name, args):
        self.calls.append(("rpc", name, args))
        if self.fail_on == name:
            raise RuntimeError(f"lỗi giả lập ở RPC {name}")
        return _RpcStub()


class _RpcStub:
    def execute(self):
        return MagicMock(
            data=[{
                "order_id": "o-1",
                "subtotal": 600000,
                "discount": 0,
                "total": 600000,
                "duplicate": False,
            }]
        )


class TestOrderIsAtomic:
    def test_du_dung_mot_rpc_deu_nhat(self):
        """Mọi bảng phải được ghi trong MỘT lệnh, không ghi tay từng bảng."""
        client = _ClientStub()
        service = OrderService(client)
        service.create_order(_order_data(), {"id": str(uuid4())})

        rpc_calls = [c for c in client.calls if c[0] == "rpc"]
        insert_calls = [c for c in client.calls if c[0] == "insert"]
        assert rpc_calls, "phải ghi đơn qua RPC để có transaction"
        assert not insert_calls, (
            "không được insert tay từng bảng — nhiều lệnh rời rạc là nguồn của "
            f"đơn lưu dở; thấy: {[c[1] for c in insert_calls]}"
        )

    def test_rpc_cha_ban_ten_dung(self):
        client = _ClientStub()
        OrderService(client).create_order(_order_data(), {"id": str(uuid4())})
        assert client.calls[0][1] == "rpc_create_order"

    def test_gui_lai_cung_mot_don_thi_khong_tao_hai_don(self):
        """Khoá idempotency: cùng khách + cùng giỏ trong thời gian ngắn → 1 đơn."""
        client = _ClientStub()
        service = OrderService(client)
        data = _order_data()

        first = service.create_order(data, {"id": str(uuid4())})
        second = service.create_order(data, {"id": str(uuid4())})

        args = client.calls[0][2]
        assert args.get("p_idempotency_key"), "phải truyền khoá idempotency"
        # Cùng dữ liệu thì cùng khoá, nên lần gửi lại trỏ về cùng đơn.
        assert first["id"] == second["id"]

    def test_rpc_that_bai_thi_khong_tao_don_nao(self):
        """Lỗi ở tầng CSDL phải nổi lên, không âm thầm trả đơn rỗng."""
        client = _ClientStub(fail_on="rpc_create_order")
        service = OrderService(client)
        with pytest.raises(OrderServiceError):
            service.create_order(_order_data(), {"id": str(uuid4())})
        assert not [c for c in client.calls if c[0] == "insert"], (
            "không được ghi bảng riêng lẻ khi RPC lỗi"
        )


class TestOrderStillValidatesBeforeWriting:
    """Việc kiểm tra phải chạy trước khi ghi, để lỗi rẻ báo cho khách."""

    def test_ngay_nhan_qua_khuong_tho_bi_chan_truoc_khi_ghi(self):
        client = _ClientStub()
        service = OrderService(client)
        data = _order_data(
            pickup_date=datetime.now(timezone.utc) + timedelta(hours=2)
        )
        with pytest.raises(OrderServiceError):
            service.create_order(data, {"id": str(uuid4())})
        assert not client.calls, "phải chặn trước khi gọi xuống CSDL"

    def test_voucher_khong_thuoc_khach_bi_chan_truoc_khi_ghi(self):
        client = _ClientStub()
        service = OrderService(client)
        data = _order_data(voucher_code="BNB-KHACNGUOI")
        with pytest.raises(OrderServiceError):
            service.create_order(data, {"id": str(uuid4())})
        assert not client.calls, (
            "voucher sai phải báo lỗi trước, không ghi đơn rồi mới báo"
        )