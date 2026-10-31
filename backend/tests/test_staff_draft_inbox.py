"""Đơn nháp của trợ lý phải HIỆN RA cho nhân viên bán hàng.

Bối cảnh đo được: backend đã cho phép `draft → pending` (chỉ staff), và
`GET /api/v1/staff/orders/{id}` đọc được đơn nháp. Nhưng danh sách hàng đợi cố ý
lọc `SALES_STATUSES = ("pending", "ready")`, giao diện chỉ vẽ pending/ready, và
nút chuyển trạng thái chỉ biết `pending → confirmed` / `ready → delivered`.

Hệ quả: đơn trợ lý vừa tạo không xuất hiện ở BẤT KỲ màn hình nào. Nhân viên
không có cách nào nhận nó trừ khi tự gọi API kèm ID. Luồng "chat → đơn nháp →
nhân viên xác nhận" bị kẹt dù từng bước riêng lẻ đều "đã có".

Test này khoá cả hai phía: danh sách phải trả về `drafts`, và UI phải có nhánh
xử lý draft. Không đụng CSDL — dùng client giả.
"""

from unittest.mock import MagicMock

import pytest

from app.api.v1.endpoints import staff_orders


class _Table:
    def __init__(self, rows: list[dict]):
        self.rows = rows

    def select(self, *_a, **_k):
        return self

    def in_(self, _column, values):
        self.rows = [r for r in self.rows if r.get("status") in values]
        return self

    def order(self, *_a, **_k):
        return self

    def execute(self):
        return MagicMock(data=self.rows)


def _db(rows: list[dict]) -> MagicMock:
    db = MagicMock()
    db.table.side_effect = lambda _name: _Table([dict(r) for r in rows])
    return db


ORDER = {"id": "aaaaaaaa-0000-0000-0000-000000000001", "status": "pending",
         "total_price": 350000, "pickup_date": "2026-11-05T10:00:00+07:00",
         "customer_name": "Khách A", "customer_phone": "0900000001",
         "customer_email": None, "created_at": "2026-11-01T09:00:00Z",
         "updated_at": "2026-11-01T09:00:00Z"}
DRAFT = {**ORDER, "id": "bbbbbbbb-0000-0000-0000-000000000002", "status": "draft",
         "customer_name": "Khách B"}


class TestQueueExposesDrafts:
    def test_danh_sach_tra_ve_don_nhap_rieng(self, monkeypatch):
        monkeypatch.setattr(
            staff_orders, "get_supabase_client", lambda **_k: _db([ORDER, DRAFT])
        )
        result = staff_orders.list_sales_orders(staff={"id": "s1", "role": "staff"})

        assert [o["id"] for o in result["drafts"]] == [DRAFT["id"]]
        assert result["draft_count"] == 1

    def test_don_nhap_khong_bi_tinh_vao_hang_doi_da_nhan(self, monkeypatch):
        monkeypatch.setattr(
            staff_orders, "get_supabase_client", lambda **_k: _db([ORDER, DRAFT])
        )
        result = staff_orders.list_sales_orders(staff={"id": "s1", "role": "staff"})

        assert [o["id"] for o in result["orders"]] == [ORDER["id"]]
        assert result["total"] == 1, (
            "đơn nháp chưa phải đơn tiệm đã nhận; không được cộng vào 'Cần xử lý'"
        )
        assert result["pending_count"] == 1
        assert result["ready_count"] == 0

    def test_draft_van_bi_loai_khoi_loc_hang_doi(self):
        """Bất biến cũ giữ nguyên: draft không lọt vào `orders`."""
        assert "draft" not in staff_orders.SALES_STATUSES
        assert "draft" in staff_orders.DRAFT_STATUSES
        assert "draft" in staff_orders.READABLE_STATUSES


def test_giao_dien_nhan_vien_co_nhanh_xu_ly_draft():
    from pathlib import Path

    source = Path(__file__).resolve().parents[2] / "frontend/src/app/staff/sales/page.tsx"
    text = source.read_text(encoding="utf-8")

    assert "drafts" in text, "trang bán hàng phải đọc danh sách đơn nháp"
    assert '"pending"' in text and "draft" in text, (
        "phải có nhánh chuyển draft → pending, nếu không nhân viên chỉ xác nhận "
        "được đơn pending/ready và đơn trợ lý tạo ra bị bỏ quên"
    )
