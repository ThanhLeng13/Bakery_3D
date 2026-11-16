"""Trợ lý không được báo sai là "bánh có sẵn trong ngày".

Lỗi người dùng báo
------------------
Khách hỏi "tìm bánh có sẵn trong ngày", trợ lý trả lời sai.

Nguyên nhân đọc được trong code: `find_cakes` chỉ đọc bảng `products`, không
đọc `product_batches`, và luôn gắn `needs_lead_hours = 0` cho mọi sản phẩm
active. Nghĩa là cả mẫu đã hết hàng hoặc chỉ nằm ở kho chung cũng được giới
thiệu là "đang có sẵn tại tiệm, bán ngay".

Cách sửa: thêm `find_ready_made_cakes` — chỉ trả về mẫu còn tồn thật theo
chi nhánh — và prompt bắt buộc dùng nó cho câu hỏi "hôm nay / có sẵn".

Các test dưới đây khoá lại cả hàm và hợp đồng prompt.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[2]


class _StubTable:
    """Builder giả lập Supabase: ghi lại tham số và trả dữ liệu theo ý test."""

    def __init__(self, data):
        self._data = data
        self.calls: list[tuple] = []

    def select(self, *args, **kwargs):
        self.calls.append(("select", args))
        return self

    def eq(self, *args):
        self.calls.append(("eq",) + args)
        return self

    def gte(self, *args):
        self.calls.append(("gte",) + args)
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args):
        return self

    def execute(self):
        return MagicMock(data=self._data)


class _Stub:
    def __init__(self, tables):
        self._tables = tables

    def table(self, name):
        return self._tables[name]


def _product(pid: str, name: str, price: int, ptype: str = "cake") -> dict:
    return {
        "id": pid,
        "name": name,
        "description": "",
        "category": "sinh nhật",
        "base_price": price,
        "sizes": ["20cm"],
        "flavors": [],
        "product_type": ptype,
        "product_3d_models": [],
    }


def _tools(products, batches, branches=None):
    from app.services.order_tools import OrderTools

    tables = {
        "products": _StubTable(products),
        "product_batches": _StubTable(batches),
        "branches": _StubTable(branches or []),
    }
    return OrderTools(_Stub(tables))


def _batch(product_id, quantity, sold=0, branch_id="b1", branch_name="Chi nhánh 1"):
    return {
        "product_id": product_id,
        "quantity": quantity,
        "quantity_sold": sold,
        "branch_id": branch_id,
        "branches": {"id": branch_id, "name": branch_name} if branch_id else None,
    }


class TestFindReadyMadeOnlyReturnsRealStock:
    def test_chi_tra_mau_con_hang(self):
        """Mẫu hết hàng không được xuất hiện trong kết quả."""
        products = [
            _product("p1", "Bánh còn hàng", 300000),
            _product("p2", "Bánh đã hết", 300000),
        ]
        batches = [
            _batch("p1", quantity=5, sold=1),
            _batch("p2", quantity=3, sold=3),  # đã bán hết
        ]
        result = _tools(products, batches).find_ready_made_cakes()

        assert result["found"] == 1
        assert [c["name"] for c in result["cakes"]] == ["Bánh còn hàng"]
        assert result["cakes"][0]["stock_total"] == 4

    def test_khong_co_lo_nao_thi_bao_khong_co(self):
        """Không có bản ghi tồn kho -> phải nói không có, không được hứa."""
        products = [_product("p1", "Bánh A", 300000)]
        result = _tools(products, []).find_ready_made_cakes()

        assert result["found"] == 0
        assert result["cakes"] == []
        assert "chưa có mẫu bánh nào còn hàng" in result["message"]
        assert "Đừng nói là còn sẵn" in result["message"]

    def test_kho_chung_duoc_tinh_vao_tong_nhung_khong_co_chi_nhanh(self):
        """Kho chung không có địa chỉ nhận nên không được gợi ý làm nơi nhận."""
        products = [_product("p1", "Bánh A", 300000)]
        batches = [_batch("p1", quantity=2, branch_id=None, branch_name=None)]
        cake = _tools(products, batches).find_ready_made_cakes()["cakes"][0]

        assert cake["stock_total"] == 2
        assert cake["branches"] == []

    def test_liet_ke_chi_nhanh_con_hang_theo_thu_tu_giam_dan(self):
        products = [_product("p1", "Bánh A", 300000)]
        batches = [
            _batch("p1", quantity=2, branch_id="b1", branch_name="Chi nhánh 1"),
            _batch("p1", quantity=7, branch_id="b2", branch_name="Chi nhánh 2"),
        ]
        cake = _tools(products, batches).find_ready_made_cakes()["cakes"][0]

        assert cake["stock_total"] == 9
        assert [b["branch_name"] for b in cake["branches"]] == [
            "Chi nhánh 2",
            "Chi nhánh 1",
        ]

    def test_loc_ngan_sach(self):
        products = [
            _product("p1", "Bánh rẻ", 200000),
            _product("p2", "Bánh đắt", 900000),
        ]
        batches = [_batch("p1", quantity=3), _batch("p2", quantity=3)]
        result = _tools(products, batches).find_ready_made_cakes(budget=300000)

        assert result["found"] == 1
        assert result["cakes"][0]["price"] == 200000

    def test_loc_tu_khoa(self):
        products = [
            _product("p1", "Bánh tiramisu", 200000),
            _product("p2", "Bánh hoa hồng", 200000),
        ]
        batches = [_batch("p1", quantity=3), _batch("p2", quantity=3)]
        result = _tools(products, batches).find_ready_made_cakes(keyword="tiramisu")

        assert result["found"] == 1
        assert result["cakes"][0]["name"] == "Bánh tiramisu"

    def test_mau_lam_san_bao_0_gio_cho(self):
        products = [_product("p1", "Bánh A", 300000)]
        batches = [_batch("p1", quantity=3)]
        cake = _tools(products, batches).find_ready_made_cakes()["cakes"][0]

        assert cake["needs_lead_hours"] == 0

    def test_ngan_sach_khong_hop_le_bao_loi(self):
        import pytest

        from app.services.order_tools import ToolError

        with pytest.raises(ToolError):
            _tools([], []).find_ready_made_cakes(budget="nhiều")


class TestToolIsWiredIntoTheAgent:
    def test_schema_co_cong_cu_moi(self):
        from app.services.order_tools import TOOL_SCHEMAS

        names = {s["function"]["name"] for s in TOOL_SCHEMAS}
        assert "find_ready_made_cakes" in names

    def test_dispatch_goi_duoc_cong_cu_moi(self):
        from app.services.order_tools import dispatch

        tools = _tools(
            [_product("p1", "Bánh A", 300000)],
            [_batch("p1", quantity=2)],
        )
        result = dispatch(tools, "find_ready_made_cakes", {})

        assert result["found"] == 1

    def test_prompt_bat_buoc_dung_cong_cu_cho_cau_hoi_trong_ngay(self):
        from app.services.rag_service import RAGService

        prompt = RAGService(MagicMock()).build_system_prompt()

        assert "find_ready_made_cakes" in prompt
        assert "hôm nay" in prompt
        assert "KHÔNG dùng `find_cakes`" in prompt
        assert "found` = 0" in prompt


class TestRecommendationCardsShowStock:
    def test_the_goi_y_hien_so_luong_con(self):
        from app.services.chat_service import ChatService

        tool_log = [
            {
                "tool": "find_ready_made_cakes",
                "result": {
                    "cakes": [
                        {
                            "id": "p1",
                            "name": "Bánh A",
                            "price": 300000,
                            "needs_lead_hours": 0,
                            "stock_total": 4,
                            "branches": [{"branch_name": "Chi nhánh 1", "quantity": 4}],
                        }
                    ]
                },
            }
        ]
        cards = ChatService._recommendations_from(tool_log)

        assert "Còn 4 cái" in cards[0]["reasoning"]
        assert "Chi nhánh 1" in cards[0]["reasoning"]
