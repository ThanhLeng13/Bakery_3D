"""Bánh sinh nhật LÀM SẴN trong danh mục phải mua liền được.

Người dùng báo: vào trang một chiếc bánh sinh nhật thì không có nút nào để mua,
và bấm "Đặt hàng ngay" thì tới trang thanh toán trống.

Nguyên nhân phía giao diện: nhánh `isCake` trong `ProductDetailClient` chỉ có
một `<Link href="/checkout">` — nó KHÔNG thêm gì vào giỏ, nên checkout thấy giỏ
rỗng và hiện "Giỏ hàng trống".

Phía server thì quy tắc đã đúng từ trước: dòng đơn có `product_id` thật được
`pricing.lead_hours_for_items` tính 0 giờ chờ. File này chốt lại hợp đồng đó để
phần sửa giao diện có chỗ dựa, và canh hai điều kiện đi kèm:

  1. `POST /api/v1/purchases` CHỈ nhận `product_type='sweet'`, nên bánh sinh nhật
     bắt buộc phải đi `POST /api/v1/orders`. Gửi sai đường là bị từ chối.
  2. Admin phải ghi được `product_type='cake'` khi tạo sản phẩm, nếu không mẫu
     mới sẽ không bao giờ vào nhóm bán ngay.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.schemas.admin_products import CreateProductRequest, UpdateProductRequest
from app.services.pricing import lead_hours_for_items


CATALOGUE_ID = "11111111-2222-3333-4444-555555555555"


class TestReadyMadeCakeSellsImmediately:
    """Mẫu làm sẵn: 0 giờ chờ."""

    def test_banh_danh_muc_mot_tang_ban_ngay(self):
        items = [{"product_id": CATALOGUE_ID, "quantity": 1}]
        assert lead_hours_for_items(items) == 0

    def test_banh_danh_muc_hai_tang_cung_ban_ngay(self):
        """Bánh hai tầng ĐÃ LÀM SẴN không cần 48 giờ: nó đã có ở tiệm."""
        items = [{"product_id": CATALOGUE_ID, "size": "2-tier", "quantity": 1}]
        assert lead_hours_for_items(items) == 0

    def test_khong_gui_customization_json_khi_mua_mau_lam_san(self):
        """Mẫu làm sẵn gửi kèm thiết kế sẽ bị tính như mẫu đặt.

        Checkout không được gửi `customization_json` cho bánh làm sẵn. Test này
        ghi lại lý do: chỉ cần món đó KHÔNG có product_id thật là mốc chờ nhảy
        lên 24/48 giờ, nên nhầm lẫn ở đây làm khách không nhận được bánh trong
        ngày.
        """
        lam_san = [{"product_id": CATALOGUE_ID, "size": "2-tier"}]
        mau_dat = [{"product_id": None, "size": "2-tier"}]

        assert lead_hours_for_items(lam_san) == 0
        assert lead_hours_for_items(mau_dat) == 48

    def test_tron_mau_dat_thi_lay_moc_cao_nhat(self):
        """Giỏ có cả mẫu làm sẵn và mẫu đặt thì phải chờ theo mẫu đặt."""
        items = [
            {"product_id": CATALOGUE_ID, "quantity": 1},
            {"product_id": None, "size": "2-tier", "quantity": 1},
        ]
        assert lead_hours_for_items(items) == 48


class TestPickupTodayIsAllowed:
    """Ngày nhận hôm nay phải hợp lệ với mẫu làm sẵn."""

    def test_nhan_sau_mot_gio_van_du_dieu_kien(self):
        items = [{"product_id": CATALOGUE_ID, "quantity": 1}]
        pickup = datetime.now(timezone.utc) + timedelta(hours=1)
        hours_until = (pickup - datetime.now(timezone.utc)).total_seconds() / 3600

        assert hours_until >= lead_hours_for_items(items)


class TestAdminCanSetProductType:
    """Admin phải tạo được mẫu bánh sinh nhật bán ngay."""

    def _payload(self, **extra):
        data = {
            "name": "Bánh sinh nhật mẫu mới",
            "description": "Mẫu làm sẵn bày tại tiệm.",
            "category": "bánh âu",
            "base_price": 350_000,
            "sizes": [{"name": "20cm", "price": 350_000}],
        }
        data.update(extra)
        return data

    def test_tao_san_pham_nhan_product_type_cake(self):
        """Trước đây schema không có trường này nên admin không nhập được."""
        req = CreateProductRequest.model_validate(self._payload(product_type="cake"))
        assert req.product_type == "cake"

    def test_mac_dinh_la_sweet_de_khong_doi_hanh_vi_cu(self):
        req = CreateProductRequest.model_validate(self._payload())
        assert req.product_type == "sweet"

    def test_tu_choi_gia_tri_la(self):
        with pytest.raises(Exception):
            CreateProductRequest.model_validate(self._payload(product_type="banh-mi"))

    def test_cap_nhat_doi_duoc_loai(self):
        req = UpdateProductRequest.model_validate({"product_type": "cake"})
        assert req.product_type == "cake"

    def test_cap_nhat_khong_truyen_thi_giu_nguyen(self):
        req = UpdateProductRequest.model_validate({"name": "Tên mới"})
        assert req.product_type is None


class TestFrontendRoutesCakesToOrders:
    """Canh giao diện gửi bánh sinh nhật sang đúng endpoint.

    Kiểm tra trên mã nguồn vì đây là bất biến dễ bị phá khi sửa checkout: đổi
    sang `/purchases` thì server từ chối ngay, nhưng không có test nào bắt được.
    """

    def _read(self, relative: str) -> str:
        from pathlib import Path

        root = Path(__file__).resolve().parents[2]
        return (root / relative).read_text(encoding="utf-8")

    def test_checkout_co_nhanh_banh_lam_san_goi_orders(self):
        src = self._read("frontend/src/app/checkout/page.tsx")

        assert "isReadyMadeCakeMode" in src, "checkout phải có chế độ bánh làm sẵn"
        # Nhánh bánh làm sẵn phải đứng TRƯỚC nhánh giỏ bánh ngọt, nếu không
        # `isCartMode` bắt hết và bánh sinh nhật lại đi vào /purchases.
        idx_ready = src.index("isReadyMadeCakeMode) {")
        idx_cart = src.index("else if (isCartMode) {")
        assert idx_ready < idx_cart, "nhánh bánh làm sẵn phải được kiểm tra trước"

    def test_trang_chi_tiet_khong_con_link_checkout_rong(self):
        """Nút cũ là <Link href="/checkout"> không thêm gì vào giỏ."""
        src = self._read("frontend/src/components/ProductDetailClient.tsx")

        assert 'id={`order-cake-${product.id}`}' not in src, (
            "link 'Đặt hàng ngay' cũ dẫn tới checkout trống, phải bỏ"
        )
        assert "productType: product.product_type" in src, (
            "món thêm vào giỏ phải mang theo loại sản phẩm"
        )
