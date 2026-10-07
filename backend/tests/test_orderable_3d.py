"""Mẫu 3D xem được không đồng nghĩa mẫu đó bán được.

Bối cảnh
--------
Quyết định 07/10/2026 của người dùng: chỉ `round-1-tier` và `round-2-tier` được
bán. Bốn mẫu còn lại — `round-3-tier`, `heart-1-tier`, `square-1-tier`,
`tall-1-tier` — chỉ xem trong phần demo.

Nhưng CSDL không lưu được ý định đó. Bảng `cake_3d_models` không có cột nào
phân biệt "xem được" với "bán được", và `product_3d_models` đang nối hai sản
phẩm hình tim vào `heart-1-tier`. Kết quả: khách thấy mẫu tim trên trang sản
phẩm, bấm mua, và đơn được tạo — trong khi bản ghi giá và lead time cho mẫu
tim chưa được duyệt để sản xuất.

Vấn đề không chỉ ở API. Nếu chỉ ẩn nút trên giao diện thì gọi thẳng API vẫn
tạo đơn được. Ràng buộc phải nằm ở server.

Cách sửa ở đây: một danh sách mẫu được phép bán, và mọi sản phẩm dùng mẫu
ngoài danh sách đó đều bị từ chối ở bước tính giá.
"""

import pytest

from app.services.orderable_3d import (
    ORDERABLE_MODEL_SLUGS,
    OrderableModelError,
    ensure_orderable_model,
    is_orderable_model,
)


class TestWhichModelsAreOrderable:
    def test_hai_mau_tron_la_mau_ban_duoc(self):
        assert is_orderable_model("round-1-tier") is True
        assert is_orderable_model("round-2-tier") is True

    def test_bon_mau_con_lai_chi_xem(self):
        for slug in ("round-3-tier", "heart-1-tier", "square-1-tier", "tall-1-tier"):
            assert is_orderable_model(slug) is False, (
                f"{slug} chỉ để xem, chưa có giá và lead time được duyệt"
            )

    def test_mau_la_hoa_thuong_khong_thoat_khoi_danh_sach(self):
        """Danh sách chỉ có đúng các mẫu đã duyệt, không tuỳ tiện thêm."""
        assert ORDERABLE_MODEL_SLUGS == ("round-1-tier", "round-2-tier")

    def test_mau_khong_ro_roi_hoac_rong(self):
        assert is_orderable_model(None) is False
        assert is_orderable_model("") is False
        assert is_orderable_model("banh-la-gi") is False


class TestEnsureOrderableModel:
    def test_mau_ban_duoc_thi_cho_qua(self):
        assert ensure_orderable_model("round-1-tier") == "round-1-tier"

    def test_mau_chi_xem_thi_bao_ly_do_ro_rang(self):
        with pytest.raises(OrderableModelError) as exc:
            ensure_orderable_model("heart-1-tier")
        message = str(exc.value)
        assert "heart-1-tier" in message, "phải nói rõ mẫu nào bị chặn"
        assert "demo" in message.lower(), "phải nói lý do: chỉ xem, chưa bán"

    def test_khong_co_mau_thi_cho_qua(self):
        """Sản phẩm không gắn mẫu nào không bị chặn — nó là sản phẩm thường."""
        assert ensure_orderable_model(None) is None

    def test_thuong_hoa_khong_doi_ket_qua(self):
        assert ensure_orderable_model(" Round-2-Tier ") == "round-2-tier"
        assert is_orderable_model(" ROUND-1-TIER ") is True