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
        """Khoá idempotency phải do khách gửi lại giữ nguyên qua các lần bấm.

        Stub trả về cùng một `order_id` cho mọi lần gọi, nên so `first["id"]`
        với `second["id"]` không chứng minh được điều gì. Điều cần khoá lại là
        hai lần gọi phải mang cùng một khoá — đó là điều `rpc_create_order` dựa
        vào để gộp đơn.
        """
        client = _ClientStub()
        service = OrderService(client)
        customer = {"id": str(uuid4())}
        data = _order_data(idempotency_key="khu-a")

        service.create_order(data, customer)
        service.create_order(data, customer)

        rpc_args = [call[2] for call in client.calls if call[0] == "rpc"]
        assert len(rpc_args) == 2
        assert rpc_args[0]["p_idempotency_key"] == "khu-a"
        assert rpc_args[1]["p_idempotency_key"] == "khu-a"

    def test_khoa_khac_thi_tao_don_khac(self):
        """Hai lần đặt khác nhau phải mang khoá khác, không gộp làm một."""
        client = _ClientStub()
        service = OrderService(client)
        customer = {"id": str(uuid4())}

        service.create_order(_order_data(idempotency_key="khu-a"), customer)
        service.create_order(_order_data(idempotency_key="khu-b"), customer)

        keys = [
            call[2]["p_idempotency_key"]
            for call in client.calls if call[0] == "rpc"
        ]
        assert keys[0] != keys[1]

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


class TestIdempotencyClaimIsCodedCorrectly:
    """Kiểm **text SQL** của RPC, vì test Python không chạy được PL/pgSQL.

    Mọi test ở trên đều giả lập ở tầng Python (`_ClientStub`), nên một lỗi
    bên trong hàm SQL — kiểu biến không khởi tạo — chạy vẫn xanh trong khi
    đặt hàng thật đã hỏng. Đúng lỗi đó đã xảy ra: `v_claimed` để NULL, nên
    `NOT COALESCE(v_claimed, FALSE)` đọc là "chưa chiếm được khoá" ngay ở lần
    gọi đầu tiên với khoá chưa từng dùng. Đo trên CSDL thật: khoá hoàn toàn mới
    trả về `23505 duplicate key`, và bảng `order_idempotency` vẫn 0 dòng —
    tức đơn đầu tiên của khách cũng không tạo được.

    Vì CI không có Postgres để chạy `CREATE FUNCTION`, cách duy nhất bắt được
    là đọc chính file migration.
    """

    def _sql(self) -> str:
        from pathlib import Path

        source = (
            Path(__file__).resolve().parents[1]
            / "migrations"
            / "add_create_order_rpc.sql"
        ).read_text(encoding="utf-8")
        return "\n".join(
            line for line in source.splitlines() if not line.lstrip().startswith("--")
        )

    def test_claimed_flag_starts_false(self):
        """`v_claimed` phải khởi tạo FALSE, không được để NULL.

        `INSERT ... ON CONFLICT DO NOTHING RETURNING ... INTO` KHÔNG gán gì khi
        có xung đột, nên biến giữ nguyên giá trị trước đó. Để NULL thì lần gọi
        đầu cũng bị đọc thành xung đột.
        """
        import re

        sql = self._sql()
        match = re.search(r"v_claimed\s+BOOLEAN\s*:?=\s*([A-Za-z]+)", sql)
        assert match, "Không thấy chỗ khai báo v_claimed trong SQL."
        assert match.group(1) == "FALSE", (
            f"v_claimed khởi tạo là {match.group(1)}, phải là FALSE — để NULL sẽ"
            " làm lần tạo đơn đầu tiên bị đọc thành trùng khoá."
        )

    def test_claim_check_distinguishes_null_from_true(self):
        """Kiểm tra phải tách NULL ra khỏi TRUE.

        `NOT COALESCE(x, FALSE)` biến NULL thành TRUE — đúng ngược ý muốn. Phải
        dùng `IS DISTINCT FROM TRUE`.
        """
        sql = self._sql()
        assert "NOT COALESCE(v_claimed" not in sql, (
            "Dùng NOT COALESCE(v_claimed, ...) sẽ đọc NULL là 'chưa chiếm được'."
            " Dùng v_claimed IS DISTINCT FROM TRUE."
        )
        assert "v_claimed IS DISTINCT FROM TRUE" in sql, (
            "Thiếu mệnh đề so NULL với TRUE đúng nghĩa."
        )

    def test_ledger_row_is_updated_not_inserted_again(self):
        """Dòng ledger phải được `UPDATE`, không được `INSERT` lần nữa.

        Đây là lỗi đã xảy ra thật trên CSDL. Hàm ghi `order_idempotency` **hai
        lần**: một lần ở đầu để chiếm khoá (chỉ có `customer_id` + `key`), một
        lần ở cuối để điền `order_id`. Lần hai là `INSERT` thuần nên đâm vào PK
        đã có:

            23505 duplicate key value violates unique constraint
                 "order_idempotency_pkey"

        Đo được: khoá hoàn toàn mới cũng lỗi, và bảng `order_idempotency` vẫn 0
        dòng — tức đơn đầu tiên của khách không tạo được. Đã thử chạy lại file
        sau khi sửa biến `v_claimed` nhưng vẫn lỗi, vì nguyên nhân nằm ở lần ghi
        thứ hai chứ không phải lần kiểm tra.
        """
        sql = self._sql()
        # Phần sau của hàm (sau khi tạo xong đơn) phải UPDATE.
        tail = sql[sql.rindex("order_status_history") :]
        assert "UPDATE public.order_idempotency" in tail, (
            "Phần điền order_id phải là UPDATE, vì dòng đã được ghi lúc chiếm"
            " khoá. INSERT lần nữa sẽ vi phạm order_idempotency_pkey."
        )
        assert "INSERT INTO public.order_idempotency" not in tail, (
            "Không được INSERT lại dòng ledger đã tồn tại."
        )