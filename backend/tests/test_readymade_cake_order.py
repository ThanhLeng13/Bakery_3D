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
from pydantic import ValidationError

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
        # `ValidationError` chứ không phải `Exception`: bắt rộng thì một lỗi gõ
        # sai tên trường trong `_payload` cũng làm test xanh.
        with pytest.raises(ValidationError):
            CreateProductRequest.model_validate(self._payload(product_type="banh-mi"))

    def test_cap_nhat_doi_duoc_loai(self):
        req = UpdateProductRequest.model_validate({"product_type": "cake"})
        assert req.product_type == "cake"

    def test_cap_nhat_khong_truyen_thi_giu_nguyen(self):
        req = UpdateProductRequest.model_validate({"name": "Tên mới"})
        assert req.product_type is None


class TestEndpointForwardsProductType:
    """Endpoint phải CHUYỂN `product_type` xuống service.

    Kiểm ở tầng endpoint, không chỉ tầng schema. Hai handler tự dựng dict rồi
    liệt kê từng trường, nên thêm trường vào schema và service là KHÔNG đủ: nếu
    handler không liệt kê thì giá trị bị bỏ lặng lẽ và admin vẫn không đổi được
    loại sản phẩm. Đúng lỗi đã xảy ra lần đầu — test chỉ kiểm schema nên không
    thấy.
    """

    def _service_spy(self, monkeypatch):
        """Thay ProductService bằng bản ghi lại tham số."""
        from app.api.v1.endpoints import admin_products as module

        captured: dict = {}

        class _Spy:
            def create_product(self, data):
                captured["create"] = data
                return {"id": "p1", **data}

            def update_product(self, product_id, data):
                captured["update"] = data
                return {"id": product_id, **data}

        monkeypatch.setattr(module, "_get_product_service", lambda: _Spy())
        return module, captured

    def test_tao_san_pham_chuyen_product_type(self, monkeypatch):
        module, captured = self._service_spy(monkeypatch)

        request = CreateProductRequest.model_validate(
            {
                "name": "Bánh sinh nhật mẫu mới",
                "description": "Mẫu làm sẵn.",
                "category": "bánh âu",
                "base_price": 350_000,
                "sizes": [{"name": "20cm", "price": 350_000}],
                "product_type": "cake",
            }
        )

        module.create_product(request=request, current_user={"role": "admin"})

        assert captured["create"]["product_type"] == "cake", (
            "handler bỏ product_type nên admin không tạo được mẫu bán ngay"
        )

    def test_cap_nhat_chuyen_product_type(self, monkeypatch):
        module, captured = self._service_spy(monkeypatch)

        request = UpdateProductRequest.model_validate({"product_type": "cake"})
        module.update_product(
            product_id="p1", request=request, current_user={"role": "admin"}
        )

        assert captured["update"]["product_type"] == "cake"

    def test_cap_nhat_khong_truyen_thi_khong_ghi_de(self, monkeypatch):
        module, captured = self._service_spy(monkeypatch)

        request = UpdateProductRequest.model_validate({"name": "Tên mới"})
        module.update_product(
            product_id="p1", request=request, current_user={"role": "admin"}
        )

        assert "product_type" not in captured["update"], (
            "không truyền thì không được ghi đè loại sản phẩm đang có"
        )


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
        #
        # Phải khớp ĐÚNG điều kiện của nhánh gửi đơn. Mẫu lỏng
        # `"isReadyMadeCakeMode) {"` còn khớp cả `if (isCakeMode ||
        # isReadyMadeCakeMode) {` trong `validateForm` — dòng đó nằm trước, nên
        # phép so sánh luôn đúng và test không kiểm được gì.
        submit_branch = "if (isReadyMadeCakeMode) {"
        assert src.count(submit_branch) == 1, (
            "cần đúng một nhánh gửi đơn cho bánh làm sẵn"
        )
        idx_ready = src.index(submit_branch)
        idx_cart = src.index("else if (isCartMode) {")
        assert idx_ready < idx_cart, "nhánh bánh làm sẵn phải được kiểm tra trước"
        # Mẫu có sẵn phải mang branch_id xuống RPC: thiếu nó thì migration mới
        # từ chối, hoặc tệ hơn một RPC cũ không thể biết trừ kho chi nhánh nào.
        ready_block = src[idx_ready:idx_cart]
        assert "branch_id: selectedBranchId!" in ready_block

    def test_mua_ngay_chi_chuyen_checkout_khi_add_item_thanh_cong(self):
        src = self._read("frontend/src/components/ProductDetailClient.tsx")
        assert "added = addItem(buildCartItem())" in src
        assert "if (added) router.push(\"/checkout\")" in src

    def test_cart_add_item_co_the_bao_tu_choi(self):
        src = self._read("frontend/src/contexts/CartContext.tsx")
        assert "addItem:" in src
        assert "=> boolean" in src
        assert "if (!confirmed) return false" in src

    def test_trang_chi_tiet_khong_con_link_checkout_rong(self):
        """Nút cũ là <Link href="/checkout"> không thêm gì vào giỏ."""
        src = self._read("frontend/src/components/ProductDetailClient.tsx")

        assert 'id={`order-cake-${product.id}`}' not in src, (
            "link 'Đặt hàng ngay' cũ dẫn tới checkout trống, phải bỏ"
        )
        assert "productType: product.product_type" in src, (
            "món thêm vào giỏ phải mang theo loại sản phẩm"
        )
        # Bánh kem mẫu sẵn cũng phải chọn đúng chi nhánh đang còn hàng. Nếu
        # khôi phục `if (!isSweet) return` thì giao diện lại hiện nút mua cho
        # cake hết hàng và khách chỉ bị từ chối sau khi điền xong checkout.
        assert "isReadyMadeCatalogueProduct" in src, (
            "mọi mẫu trong danh mục phải đọc tồn theo chi nhánh"
        )
        assert "if (!isReadyMadeCatalogueProduct) return;" in src, (
            "không được chỉ fetch tồn kho cho sweet"
        )
        assert "branch.branch_id !== null && branch.quantity_available > 0" in src, (
            "Kho chung không có branch UUID không được phép mua nhận tại chi nhánh"
        )
        assert "setStockByBranch(initialStockByBranch ?? null)" in src, (
            "refresh lỗi phải giữ snapshot SSR thay vì làm mất tồn kho đã biết"
        )

    def test_product_detail_fetches_stock_for_cake_catalogue_too(self):
        src = self._read("frontend/src/app/products/[id]/page.tsx")
        assert "product.product_type === \"sweet\"" not in src, (
            "trang chi tiết không được chỉ fetch tồn cho sweet"
        )
        assert "getStockByBranch(params.id)" in src

    def test_inventory_search_loads_all_products_not_only_sweets(self):
        src = self._read("frontend/src/app/baker/inventory/page.tsx")
        assert "category=b%C3%A1nh+ng%E1%BB%8Dt" not in src
        assert "product_type === \"sweet\"" not in src
        assert "page_size=100" in src
        assert "Tên và giá luôn lấy theo sản phẩm hiện tại" in src

    def test_banh_sinh_nhat_khong_co_o_chon_kich_co_doi_gia(self):
        """Giá hiển thị phải bằng giá bị tính.

        Khi mở bán bánh sinh nhật, ô chọn kích cỡ vẫn còn và khối "Chi tiết giá"
        vẫn cộng theo kích cỡ + hương vị, trong khi `buildCartItem` gửi
        `base_price` và server cũng tính `base_price`
        (`order_service._catalog_price` chỉ đọc cột đó, không xét kích cỡ).
        Khách chọn 24cm thấy 450.000đ rồi bị tính 320.000đ — đúng loại lỗi mà
        `pricing.py` ghi là đã gây lệch 130.000đ mỗi đơn.

        Mua liền là mua đúng chiếc đang bày bán. Đổi kích cỡ là làm bánh mới,
        tức mẫu đặt qua Studio với mốc chờ 24/48 giờ.
        """
        src = self._read("frontend/src/components/ProductDetailClient.tsx")

        assert "isCake && product.sizes.length > 0" in src, (
            "bánh sinh nhật phải hiện kích cỡ ở dạng CHỈ ĐỌC, không phải ô chọn "
            "làm đổi giá"
        )
        assert "!isCake && product.sizes.length > 0" in src, (
            "ô chọn kích cỡ đổi giá chỉ dành cho sản phẩm không phải bánh kem"
        )
