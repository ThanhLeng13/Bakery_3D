"""Áp dụng voucher khi tạo đơn.

Bối cảnh
--------
`POST /api/v1/loyalty/redeem` đổi điểm thành mã voucher giảm 5.000đ và ghi vào
bảng `vouchers`. Trước đây không nơi nào đọc bảng đó: khách đổi điểm xong không
dùng được mã. Gói 1 của kế hoạch 07/10 yêu cầu voucher phải chạy được.

Nguyên tắc: **server quyết định mọi con số.** Mã do khách nhập, nhưng
`discount_vnd` đọc từ bảng `vouchers`, không bao giờ lấy từ phía trình duyệt.
"""

import logging
from datetime import datetime, timezone

_logger = logging.getLogger(__name__)


class VoucherServiceError(Exception):
    """Voucher không hợp lệ hoặc không dùng được."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _expiry_is_future(expires_at) -> bool:
    """Voucher còn hiệu lực. `expires_at` rỗng nghĩa là không hạn."""
    if not expires_at:
        return True
    try:
        expiry = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
    except ValueError:
        # Ngày hạn hỏng thì không tin vào nó: coi như đã hết hạn cho an toàn.
        return False
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    return expiry > _now()


def max_discount_for(total: int, discount_vnd: int) -> int:
    """Số tiền giảm thực tế, không bao giờ vượt quá tổng hàng.

    Tổng âm là dữ liệu hỏng; trả về 0 để không biến giảm thành số âm rồi cộng
    ngược vào hoá đơn.
    """
    if not isinstance(total, int) or not isinstance(discount_vnd, int):
        return 0
    if total <= 0 or discount_vnd <= 0:
        return 0
    return min(discount_vnd, total)


def apply_voucher(priced: dict, voucher: dict | None, *, customer_id: str | None = None, code: str | None = None) -> dict:
    """Tính lại tổng tiền sau khi áp voucher.

    Args:
        priced: dict có `total` — giá server đã quyết định.
        voucher: dòng bảng `vouchers`, hoặc None nếu khách không nhập mã.
        customer_id: khách đang đặt; voucher phải thuộc đúng người này.
        code: mã khách nhập, chỉ dùng để báo lỗi khi không tìm thấy voucher.

    Returns:
        dict có subtotal, discount, total, voucher_code, voucher_id.

    Raises:
        VoucherServiceError: mã không tồn tại, hết hạn, đã dùng, hoặc không
            thuộc khách này.
    """
    total = priced.get("total", 0)
    result = {
        "subtotal": total,
        "discount": 0,
        "total": total,
        "voucher_code": None,
        "voucher_id": None,
    }

    if voucher is None:
        if code:
            raise VoucherServiceError(
                f"Voucher '{code}' không tồn tại hoặc không còn hiệu lực."
            )
        return result

    if customer_id is not None and str(voucher.get("user_id")) != str(customer_id):
        raise VoucherServiceError("Voucher này không thuộc tài khoản của bạn.")

    if voucher.get("status") == "used" or voucher.get("used_at"):
        raise VoucherServiceError("Voucher này đã được sử dụng.")

    if not _expiry_is_future(voucher.get("expires_at")):
        raise VoucherServiceError("Voucher này đã hết hạn.")

    discount = max_discount_for(total, voucher.get("discount_vnd") or 0)
    result["discount"] = discount
    result["total"] = total - discount
    result["voucher_code"] = voucher.get("code")
    result["voucher_id"] = voucher.get("id")
    return result


class VoucherService:
    """Tra cứu voucher trong CSDL."""

    def __init__(self, db):
        self._db = db

    def find_usable(self, code: str, customer_id: str) -> dict | None:
        """Tìm voucher đúng mã và thuộc đúng khách.

        Trả None nếu không có hoặc không dùng được, để tầng trên báo lỗi rõ
        bằng thông điệp thân thiện thay vì lộ chi tiết CSDL.
        """
        if not code:
            return None
        clean = str(code).strip().upper()
        result = (
            self._db.table("vouchers")
            .select("id, code, user_id, discount_vnd, status, expires_at, used_at")
            .eq("code", clean)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        if not rows:
            return None
        voucher = rows[0]
        if str(voucher.get("user_id")) != str(customer_id):
            return None
        return voucher

    def mark_used(self, voucher_id: str) -> None:
        """Đánh dấu voucher đã dùng.

        Dùng `eq('status', 'active')` để chỉ chuyển một lần: nếu hai request
        cùng lúc dùng chung mã, chỉ một cái thành công, cái còn lại nhận 0
        dòng cập nhật và đã có bản ghi nhưng mã vẫn không bị ghi đè.
        """
        result = (
            self._db.table("vouchers")
            .update({"status": "used", "used_at": _now().isoformat()})
            .eq("id", voucher_id)
            .eq("status", "active")
            .execute()
        )
        if not result.data:
            _logger.warning(
                "Voucher %s không chuyển sang 'used' được — có thể đã dùng "
                "hoặc bị huỷ trong lúc xử lý.",
                voucher_id,
            )