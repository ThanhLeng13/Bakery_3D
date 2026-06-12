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
        le=10,
        description="Số voucher muốn đổi (mỗi voucher = 100 điểm = 5,000 VND)",
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
    Đổi điểm lấy voucher giảm giá.

    Mỗi lần đổi:  100 điểm → 1 voucher → giảm 5,000 VND.
    Tối đa:        10 voucher / lần (= 1,000 điểm = 50,000 VND).

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
