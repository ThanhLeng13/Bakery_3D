"""Trợ lý phải chặn mẫu 3D chỉ-để-xem giống hệt checkout.

Vì sao cần: `OrderService._catalog_price` đã gọi `ensure_orderable_model` nên
đường checkout không tạo được đơn cho sản phẩm gắn `heart-1-tier`. Nhưng trợ lý
đi đường khác — `OrderTools.price_order` → `create_draft_order` — và trước đây
đường đó chỉ đọc `products.base_price`, không hề hỏi mẫu 3D. Kết quả: cùng một
sản phẩm, khách tự đặt thì bị chặn, còn nhờ trợ lý đặt thì tạo được nháp.

Test dùng client giả, không kết nối CSDL thật.
"""

from unittest.mock import MagicMock

import pytest

from app.services.order_tools import OrderTools, ToolError


def _client(products: list[dict]) -> MagicMock:
    client = MagicMock()
    client.table.return_value.select.return_value.eq.return_value.execute.return_value = (
        MagicMock(data=products)
    )
    return client


def _product(slug: str | None, *, product_id: str, name: str, price: int = 300000) -> dict:
    if slug is None:
        links: list[dict] = []
    else:
        links = [{
            "is_primary": True,
            "cake_3d_models": {"id": "model-1", "slug": slug},
        }]
    return {
        "id": product_id,
        "name": name,
        "description": "",
        "category": "sinh nhat",
        "base_price": price,
        "sizes": [{"name": "20cm", "price": price}],
        "flavors": [],
        "product_type": "cake",
        "product_3d_models": links,
    }


PREVIEW_ID = "22222222-2222-2222-2222-222222222222"
ORDERABLE_ID = "11111111-1111-1111-1111-111111111111"


class TestPriceOrderRejectsPreviewOnlyModel:
    def test_khong_bao_gia_duoc_cho_mau_chi_xem(self):
        product = _product("heart-1-tier", product_id=PREVIEW_ID, name="Bánh hình tim")
        tools = OrderTools(_client([product]))

        with pytest.raises(ToolError) as exc:
            tools.price_order([{"cake_id": PREVIEW_ID, "quantity": 1}])

        assert "chưa mở bán" in str(exc.value), (
            "phải từ chối thẳng, không được báo giá cho mẫu chưa duyệt"
        )

    def test_van_bao_gia_binh_thuong_cho_mau_duoc_ban(self):
        product = _product("round-2-tier", product_id=ORDERABLE_ID, name="Bánh tròn 2 tầng")
        tools = OrderTools(_client([product]))

        priced = tools.price_order([{"cake_id": ORDERABLE_ID, "quantity": 2}])

        assert priced["total_price"] == 600000

    def test_san_pham_khong_gan_mau_3d_khong_bi_chan(self):
        product = _product(None, product_id=ORDERABLE_ID, name="Bánh bông lan")
        tools = OrderTools(_client([product]))

        assert tools.price_order([{"cake_id": ORDERABLE_ID, "quantity": 1}])["total_price"] == 300000


class TestListingHidesPreviewOnly:
    def test_goi_y_khong_dua_mau_chi_xem_ra(self):
        preview = _product("heart-1-tier", product_id=PREVIEW_ID, name="Bánh hình tim", price=100000)
        sellable = _product("round-1-tier", product_id=ORDERABLE_ID, name="Bánh tròn", price=900000)
        tools = OrderTools(_client([preview, sellable]))

        result = tools.find_cakes(budget=50)  # dưới mọi giá -> nhánh "gợi ý"

        names = [s["name"] for s in result["suggestions"]]
        assert names == ["Bánh tròn"], (
            "gợi ý không được chứa mẫu chỉ-để-xem, nếu không khách chọn rồi bị từ chối"
        )

    def test_loc_chu_khoa_van_giu_nguyen_ket_qua(self):
        """Không được lọc mất kết quả bình thường khi lọc gợi ý."""
        sellable = _product("round-1-tier", product_id=ORDERABLE_ID, name="Bánh kem dâu")
        tools = OrderTools(_client([sellable]))

        result = tools.find_cakes(keyword="dâu")

        assert [c["name"] for c in result["cakes"]] == ["Bánh kem dâu"]

    def test_ket_qua_binh_thuong_cung_khong_chua_mau_chi_xem(self):
        """Không chỉ nhánh gợi ý — danh sách `cakes` cũng phải sạch.

        Trước đây chỉ nhánh "không tìm thấy gì" lọc mẫu chỉ-để-xem, còn kết quả
        bình thường vẫn trả về chúng. Trợ lý giới thiệu một mẫu khách không đặt
        được là thông tin sai, và `found` cũng đếm sai.
        """
        preview = _product("heart-1-tier", product_id=PREVIEW_ID, name="Bánh hình tim")
        sellable = _product("round-1-tier", product_id=ORDERABLE_ID, name="Bánh tròn")
        tools = OrderTools(_client([preview, sellable]))

        result = tools.find_cakes()  # không ngân sách, không từ khoá

        assert [c["name"] for c in result["cakes"]] == ["Bánh tròn"]
        assert result["found"] == 1, "found phải đếm sau khi lọc, không đếm mẫu chỉ-xem"

    def test_loc_theo_dip_cung_khong_lo_mau_chi_xem(self):
        preview = _product("square-1-tier", product_id=PREVIEW_ID, name="Bánh vuông")
        sellable = _product("round-1-tier", product_id=ORDERABLE_ID, name="Bánh tròn")
        tools = OrderTools(_client([preview, sellable]))

        result = tools.find_cakes(occasion="sinh nhật")

        assert [c["name"] for c in result["cakes"]] == ["Bánh tròn"]
