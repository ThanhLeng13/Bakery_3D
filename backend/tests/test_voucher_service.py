"""Voucher phải dùng được thật khi đặt hàng.

Bối cảnh
--------
Khách đổi điểm qua `POST /api/v1/loyalty/redeem`, nhận mã voucher giảm 5.000đ,
mã được ghi vào bảng `vouchers` (RPC `rpc_redeem_points` chạy tốt, có kiểm tra
đủ điểm và chống đổi trùng). Nhưng **không có chỗ nào đọc bảng `vouchers`**:
`CreateOrderRequest` không có trường voucher, `create_order` không tính giảm,
và không endpoint nào cho nhập mã. Khách đổi điểm xong không dùng được.

Quyết định 07/10/2026: voucher phải dùng được trong đơn. Ràng buộc:

- Server là nguồn quyết định — khách tự khai `discount_vnd` không được.
- Mã phải thuộc đúng khách, còn hiệu lực, chưa dùng, và hết hạn chưa tới.
- Tổng tiền không được âm; giảm không được vượt quá giá trị voucher.
- Dùng xong thì mã chuyển sang 'used' — không dùng lại được.
- Không có voucher thì đơn vẫn tạo bình thường.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.services.voucher_service import (
    VoucherServiceError,
    apply_voucher,
    max_discount_for,
)


def _voucher(**over):
    """Một voucher hợp lệ; ghi đè tuỳ ý để tạo ca lỗi."""
    base = {
        "id": "v-1",
        "code": "BNB-ABCD1234",
        "user_id": "u-1",
        "discount_vnd": 5000,
        "status": "active",
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        "used_at": None,
    }
    base.update(over)
    return base


class TestApplyVoucher:
    def test_voucher_hop_le_giam_dung_so_tien(self):
        bd = apply_voucher({"total": 480_000}, _voucher())
        assert bd["subtotal"] == 480_000
        assert bd["discount"] == 5000
        assert bd["total"] == 475_000

    def test_khong_co_voucher_thi_giu_nguyen_tong(self):
        """Không nhập mã thì đơn vẫn tạo bình thường."""
        bd = apply_voucher({"total": 480_000}, None)
        assert bd["subtotal"] == 480_000
        assert bd["discount"] == 0
        assert bd["total"] == 480_000
        assert bd["voucher_code"] is None
        assert bd["voucher_id"] is None

    def test_giam_khong_duoc_lon_hon_tong_hang(self):
        """Voucher 50.000đ trên đơn 30.000đ thì chỉ giảm 30.000đ, không âm."""
        bd = apply_voucher({"total": 30_000}, _voucher(discount_vnd=50_000))
        assert bd["discount"] == 30_000
        assert bd["total"] == 0
        assert bd["total"] >= 0

    def test_tong_bang_0_thi_khong_bi_am(self):
        bd = apply_voucher({"total": 0}, _voucher())
        assert bd["total"] == 0
        assert bd["discount"] == 0


class TestVoucherRejection:
    def test_ma_da_dung_bi_tu_choi(self):
        with pytest.raises(VoucherServiceError, match="sử dụng"):
            apply_voucher({"total": 100_000}, _voucher(status="used"))

    def test_ma_da_dung_theo_used_at_bi_tu_choi(self):
        """Trạng thái ghi 'active' nhưng đã có used_at vẫn phải bị chặn."""
        used_at = datetime.now(timezone.utc).isoformat()
        with pytest.raises(VoucherServiceError, match="sử dụng"):
            apply_voucher({"total": 100_000}, _voucher(used_at=used_at))

    def test_ma_het_han_bi_tu_choi(self):
        qua = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        with pytest.raises(VoucherServiceError, match="hết hạn"):
            apply_voucher({"total": 100_000}, _voucher(expires_at=qua))

    def test_ma_khong_cua_khach_nay_bi_tu_choi(self):
        """Không dùng được mã của người khác — kiểm tra ở tầng truy vấn."""
        with pytest.raises(VoucherServiceError, match="không thuộc"):
            apply_voucher(
                {"total": 100_000},
                _voucher(),
                customer_id="u-khac",
            )

    def test_voucher_khong_ton_tai_bao_loi_rõ(self):
        with pytest.raises(VoucherServiceError):
            apply_voucher({"total": 100_000}, None, code="BNB-KHONGCO")


class TestMaxDiscount:
    def test_chi_giam_toc_da_phu_khong_vuot_tong(self):
        assert max_discount_for(30_000, 50_000) == 30_000
        assert max_discount_for(100_000, 50_000) == 50_000
        assert max_discount_for(0, 50_000) == 0

    def test_so_tien_am_khong_duoc_dung(self):
        """Giá âm là dữ liệu hỏng; không được nhân thành giảm âm (tức tăng tiền)."""
        assert max_discount_for(-1000, 5000) == 0