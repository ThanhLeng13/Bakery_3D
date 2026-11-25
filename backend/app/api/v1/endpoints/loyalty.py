"""Loyalty Points API Endpoints — Hệ thống tích điểm.

Endpoints:
    GET  /api/v1/loyalty/me       — Xem số điểm + lịch sử giao dịch
    POST /api/v1/loyalty/redeem   — Đổi điểm lấy voucher giảm giá
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.dependencies import get_current_user, get_supabase_client
from app.services.loyalty_service import (
    InsufficientPointsError,
    LoyaltyService,
    LoyaltyServiceError,
)
from app.services.voucher_service import (
    VoucherService,
    VoucherServiceError,
    apply_voucher,
)

router = APIRouter()


# ─── Dependency ────────────────────────────────────────────────────────────────

def _get_loyalty_svc() -> LoyaltyService:
    """Tạo LoyaltyService với service-role client (bypass RLS để ghi)."""
    db = get_supabase_client(use_service_role=True)
    return LoyaltyService(db)


# ─── Schemas ───────────────────────────────────────────────────────────────────

class RedeemRequest(BaseModel):
    voucher_count: int = Field(
        default=1,
        ge=1,
        le=10000,
        description="Số mốc 100 điểm muốn đổi (mỗi mốc = 5,000 VND, cộng dồn vào 1 voucher)",
    )


class MergeVouchersRequest(BaseModel):
    voucher_ids: list[str] | None = Field(
        default=None,
        description="Danh sách ID voucher cần gộp; bỏ trống để gộp toàn bộ voucher đang dùng được.",
    )


class VoucherCheckRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=64, description="Mã voucher")
    order_total: int = Field(
        ...,
        ge=0,
        description="Tạm tính của đơn, để server tính mức giảm thực tế.",
    )


# ─── Routes ────────────────────────────────────────────────────────────────────

@router.get("/me")
def get_my_loyalty(
    user: dict = Depends(get_current_user),
):
    """
    Lấy thông tin điểm tích lũy + lịch sử 20 giao dịch gần nhất.

    Yêu cầu đăng nhập (Customer / Baker / Admin đều xem được điểm của mình).
    """
    svc = _get_loyalty_svc()

    balance = svc.get_balance(user["id"])
    transactions = svc.get_transactions(user["id"], limit=20)

    return {
        **balance,
        "transactions": transactions,
    }


@router.post("/redeem")
def redeem_points(
    body: RedeemRequest,
    user: dict = Depends(get_current_user),
):
    """
    Đổi điểm lấy 1 voucher giảm giá (cộng dồn theo số điểm đổi).

    Mỗi mốc 100 điểm = 5,000 VND giảm giá. Có thể đổi nhiều mốc cùng lúc
    dựa trên số điểm hiện có để nhận 1 voucher giá trị lớn hơn.

    Yêu cầu đăng nhập.
    """
    svc = _get_loyalty_svc()

    try:
        result = svc.redeem_points(user["id"], body.voucher_count)
        return result
    except InsufficientPointsError as e:
        raise HTTPException(status_code=400, detail=e.message) from e
    except LoyaltyServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get("/vouchers")
def list_my_vouchers(
    user: dict = Depends(get_current_user),
):
    """Danh sách voucher của chính khách, kèm mã để nhập ở trang thanh toán.

    Vì sao cần: sau khi đổi điểm, màn hình thành công có hiện mã nhưng chỉ một
    lần. Khách đóng đi là mất dấu — không có chỗ nào xem lại, nên họ không nhập
    được mã khi đặt hàng và tưởng lần đổi điểm bị lỗi. Đây là nguồn để trang
    thanh toán gợi ý mã đang dùng được.
    """
    db = get_supabase_client(use_service_role=True)
    result = (
        db.table("vouchers")
        .select("id, code, discount_vnd, status, expires_at, used_at, created_at")
        .eq("user_id", user["id"])
        .order("status", desc=False)
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )
    rows = result.data or []

    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)

    def _usable(row: dict) -> bool:
        if row.get("status") != "active" or row.get("used_at"):
            return False
        expires = row.get("expires_at")
        if not expires:
            return True
        try:
            parsed = datetime.fromisoformat(str(expires).replace("Z", "+00:00"))
        except ValueError:
            return False
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed > now

    return {
        "vouchers": rows,
        "usable_count": sum(1 for row in rows if _usable(row)),
        "total_discount_available": sum(
            row.get("discount_vnd") or 0 for row in rows if _usable(row)
        ),
    }


@router.post("/vouchers/check")
def check_voucher(
    body: VoucherCheckRequest,
    user: dict = Depends(get_current_user),
):
    """Kiểm tra một mã voucher TRƯỚC khi đặt hàng và trả mức giảm thực tế.

    Nhờ endpoint này khách thấy ngay "giảm 5.000đ" khi nhập mã, thay vì bấm đặt
    hàng rồi mới biết mã sai hoặc hết hạn. Server vẫn là nơi quyết định con số;
    frontend chỉ hiển thị lại.
    """
    db = get_supabase_client(use_service_role=True)
    voucher_row = VoucherService(db).find_usable(body.code, str(user["id"]))

    try:
        money = apply_voucher(
            {"total": int(body.order_total)},
            voucher_row,
            customer_id=str(user["id"]),
            code=body.code,
        )
    except VoucherServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    return {
        "valid": True,
        "code": money["voucher_code"],
        "subtotal": money["subtotal"],
        "discount": money["discount"],
        "total": money["total"],
        "message": (
            f"Áp dụng được, giảm {money['discount']:,}đ."
            if money["discount"] > 0
            else "Mã hợp lệ nhưng đơn chưa đủ điều kiện giảm giá."
        ),
    }


@router.post("/vouchers/merge")
def merge_my_vouchers(
    body: MergeVouchersRequest | None = None,
    user: dict = Depends(get_current_user),
):
    """Gộp nhiều voucher còn hiệu lực của khách thành 1 voucher cộng dồn."""
    svc = _get_loyalty_svc()
    voucher_ids = body.voucher_ids if body else None
    try:
        return svc.merge_vouchers(str(user["id"]), voucher_ids=voucher_ids)
    except LoyaltyServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
