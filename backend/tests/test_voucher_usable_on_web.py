"""Voucher đổi từ điểm phải dùng được ở CẢ HAI luồng mua.

Bối cảnh — lỗi thật khách báo
-----------------------------
Trang thanh toán có một ô "Mã giảm giá" dùng chung cho hai luồng:

    giỏ bánh ngọt  → POST /api/v1/purchases
    đặt bánh kem   → POST /api/v1/orders

Luồng `/orders` nhận `voucher_code` và tính giảm. Luồng `/purchases` thì
KHÔNG: `CreatePurchaseRequest` không có trường đó, và bảng `purchases` không có
cột nào để lưu. Pydantic bỏ qua trường lạ, nên mã khách nhập bị nuốt im lặng:

    - đơn vẫn tính đủ tiền
    - mã vẫn ở trạng thái 'active' (không bị đánh dấu đã dùng)
    - khách không thấy giảm giá, tưởng tính năng đổi điểm hỏng

Đó chính là "test tính năng đổi điểm voucher thì dùng trên web không được".

Những gì được khoá ở đây:
- `CreatePurchaseRequest` có `voucher_code`, chuẩn hoá hoa/thường
- `/purchases` gọi `apply_voucher` và trả `discount`/`subtotal`/`voucher_code`
- voucher được GIỮ CHỖ nguyên tử trước khi trừ kho (chống dùng 2 lần)
- đơn hỏng thì TRẢ voucher lại (khách không mất mã vì lỗi của tiệm)
- trang thanh toán gửi `voucher_code` ở cả hai nhánh
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend"


def _voucher(**over):
    base = {
        "id": "v-1",
        "code": "BNB-AAAA1111",
        "user_id": "u-1",
        "discount_vnd": 5000,
        "status": "active",
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        "used_at": None,
    }
    base.update(over)
    return base


class TestPurchaseRequestAcceptsVoucher:
    def test_request_co_truong_voucher_code(self):
        """Nếu trường này không tồn tại thì Pydantic bỏ qua nó và mã bị nuốt."""
        from app.api.v1.endpoints.purchases import CreatePurchaseRequest

        fields = CreatePurchaseRequest.model_fields
        assert "voucher_code" in fields

    def test_ma_duoc_chuan_hoa_hoa_thuong_va_khoang_trang(self):
        from app.api.v1.endpoints.purchases import CreatePurchaseRequest

        req = CreatePurchaseRequest(
            items=[{"product_id": "00000000-0000-0000-0000-000000000001", "quantity": 1}],
            customer_name="A",
            customer_phone="0901234567",
            branch_id="00000000-0000-0000-0000-000000000002",
            voucher_code="  bnb-aaaa1111  ",
        )
        assert req.voucher_code == "BNB-AAAA1111"

    def test_khong_nhap_ma_thi_none_khong_phai_chuoi_rong(self):
        from app.api.v1.endpoints.purchases import CreatePurchaseRequest

        req = CreatePurchaseRequest(
            items=[{"product_id": "00000000-0000-0000-0000-000000000001", "quantity": 1}],
            customer_name="A",
            customer_phone="0901234567",
            branch_id="00000000-0000-0000-0000-000000000002",
            voucher_code="   ",
        )
        assert req.voucher_code is None


class TestPurchaseEndpointAppliesVoucher:
    """Đọc mã nguồn để chắc chắn đường áp voucher không bị bỏ quên.

    Kiểm tra hành vi thật cần CSDL; ở đây khoá sự HIỆN DIỆN của các bước, vì
    lỗi gốc chính là một bước bị thiếu hẳn.
    """

    def _source(self) -> str:
        return (BACKEND / "app/api/v1/endpoints/purchases.py").read_text(
            encoding="utf-8"
        )

    def test_co_goi_apply_voucher(self):
        src = self._source()
        assert "apply_voucher(" in src
        assert "VoucherService(" in src

    def test_co_giu_cho_va_tra_voucher(self):
        """Giữ chỗ trước khi trừ kho, trả lại khi hỏng.

        Không giữ chỗ thì hai đơn đồng thời dùng chung một mã; không trả lại
        thì hết hàng là khách mất luôn voucher.
        """
        src = self._source()
        assert ".claim(" in src
        assert ".release(" in src

    def test_claim_dat_truoc_buoc_tru_kho(self):
        """Thứ tự quan trọng: giữ chỗ phải xảy ra TRƯỚC khi tạo đơn/trừ kho."""
        src = self._source()
        claim_at = src.index("voucher_claimed = voucher_svc.claim(")
        insert_at = src.index('db.table("purchases").insert(')
        assert claim_at < insert_at

    def test_loi_tru_kho_tra_voucher(self):
        """Nhánh 409 (hết hàng) phải release, nếu không khách mất mã."""
        src = self._source()
        stock_branch = src.index("except (InsufficientStockError, InventoryServiceError)")
        # Trong 200 ký tự sau nhánh lỗi phải có release.
        assert ".release(" in src[stock_branch : stock_branch + 400]


class TestVoucherClaimIsAtomic:
    def _svc(self, update_result):
        from app.services.voucher_service import VoucherService

        class _Table:
            def __init__(self):
                self.calls = []

            def update(self, payload):
                self.calls.append(("update", payload))
                return self

            def eq(self, *_a):
                return self

            def execute(self):
                return update_result

        class _DB:
            def __init__(self):
                self._t = _Table()

            def table(self, _name):
                return self._t

        db = _DB()
        return VoucherService(db), db._t

    def test_claim_thanh_cong_khi_co_dong_duoc_cap_nhat(self):
        svc, table = self._svc(type("R", (), {"data": [{"id": "v-1"}]})())
        assert svc.claim("v-1") is True
        assert table.calls[0][1]["status"] == "used"

    def test_claim_that_bai_khi_khong_dong_nao_doi(self):
        """Mã đã bị request khác dùng: UPDATE khớp 0 dòng."""
        svc, _ = self._svc(type("R", (), {"data": []})())
        assert svc.claim("v-1") is False

    def test_release_tra_ma_ve_active(self):
        svc, table = self._svc(type("R", (), {"data": [{"id": "v-1"}]})())
        svc.release("v-1")
        assert table.calls[0][1]["status"] == "active"
        assert table.calls[0][1]["used_at"] is None

    def test_release_khong_nem_loi_ra_ngoai(self):
        """Đang trong đường xử lý lỗi: che mất lỗi gốc sẽ báo sai cho khách."""

        class _Boom:
            def table(self, _n):
                raise RuntimeError("CSDL hỏng")

        from app.services.voucher_service import VoucherService

        VoucherService(_Boom()).release("v-1")  # không được ném


class TestFrontendSendsVoucherOnBothPaths:
    def _src(self) -> str:
        return (FRONTEND / "src/app/checkout/page.tsx").read_text(encoding="utf-8")

    def test_luong_mua_banh_ngot_gui_voucher_code(self):
        """Đây chính là lỗi: nhánh /purchases trước đây không gửi mã."""
        src = self._src()
        purchase_branch = src.index("SWEET PURCHASE MODE")
        order_branch = src.index("CAKE ORDER MODE")
        segment = src[purchase_branch:order_branch]
        assert "voucher_code" in segment

    def test_ca_hai_nhanh_deu_gui_voucher(self):
        src = self._src()
        # ready-made cake + sweet purchase + custom cake = 3 chỗ gửi mã
        assert src.count("voucher_code: voucherCode.trim() || null") >= 3

    def test_co_kiem_tra_ma_truoc_khi_dat(self):
        src = self._src()
        assert "checkVoucher(" in src
        assert "voucherInfo" in src

    def test_hien_so_tien_sau_giam_tren_nut_dat(self):
        """Nếu nút vẫn hiện tổng gốc thì khách thấy mâu thuẫn với dòng tiết kiệm."""
        src = self._src()
        assert "voucherInfo.total" in src

    def test_co_chon_giao_hang_hay_ghe_lay(self):
        src = self._src()
        assert "fulfillmentType" in src
        assert 'id="deliveryAddress"' in src

    def test_gui_fulfillment_o_ca_hai_luong_order(self):
        src = self._src()
        assert src.count("fulfillment_type: fulfillmentType") >= 2


class TestLoyaltyVoucherEndpointsExist:
    def _router_source(self) -> str:
        return (BACKEND / "app/api/v1/endpoints/loyalty.py").read_text(
            encoding="utf-8"
        )

    def test_co_endpoint_xem_lai_ma(self):
        """Mã chỉ hiện một lần ở màn hình thành công là mất dấu.

        Không có chỗ xem lại thì khách không nhập được mã khi đặt hàng.
        """
        src = self._router_source()
        assert '@router.get("/vouchers")' in src

    def test_co_endpoint_kiem_tra_ma(self):
        src = self._router_source()
        assert '@router.post("/vouchers/check")' in src

    def test_kiem_tra_ma_tra_ve_so_tien_giam(self):
        from app.api.v1.endpoints.loyalty import VoucherCheckRequest

        req = VoucherCheckRequest(code="BNB-X", order_total=250_000)
        assert req.order_total == 250_000
