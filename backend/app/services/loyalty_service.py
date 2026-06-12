"""Loyalty Points Service — Hệ thống tích điểm Bơ Nơ Bakery.

Quy tắc tích điểm:
    Mua bánh ngọt (purchases): 1 điểm / 1,000 VND (làm tròn xuống)
    Đặt bánh kem (orders):     1.5 điểm / 1,000 VND (làm tròn xuống)
    Đổi điểm:                  100 điểm = 5,000 VND giảm giá

Bảng Supabase:
    loyalty_points       — số dư điểm hiện tại của mỗi user
    loyalty_transactions — lịch sử từng giao dịch điểm
"""

import logging
import math
from typing import Any

_logger = logging.getLogger(__name__)

# ─── Hằng số quy tắc ──────────────────────────────────────────────────────────

# Số điểm trên mỗi 1,000 VND cho từng loại
POINTS_PER_1000_VND_PURCHASE = 1.0    # bánh ngọt
POINTS_PER_1000_VND_ORDER    = 1.5    # bánh kem đặt trước

# Quy đổi khi dùng điểm
REDEEM_POINTS_PER_VOUCHER  = 100      # số điểm cần để đổi một lượt
REDEEM_VALUE_PER_VOUCHER   = 5_000    # VND được giảm mỗi lượt 100 điểm

# Số điểm tối đa có thể đổi trong một lần
MAX_REDEEM_AT_ONCE = 1_000            # = 50,000 VND


# ─── Exceptions ───────────────────────────────────────────────────────────────

class LoyaltyServiceError(Exception):
    """Base exception for loyalty service."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class InsufficientPointsError(LoyaltyServiceError):
    """User does not have enough points to redeem."""

    def __init__(self, available: int, requested: int):
        super().__init__(
            f"Không đủ điểm để đổi. Hiện có {available} điểm, cần {requested} điểm.",
            status_code=400,
        )


# ─── Service ──────────────────────────────────────────────────────────────────

class LoyaltyService:
    """Nghiệp vụ hệ thống tích điểm."""

    def __init__(self, supabase_client: Any):
        self._db = supabase_client

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def calc_points_for_purchase(total_vnd: int) -> int:
        """Tính điểm khi mua bánh ngọt."""
        return math.floor(total_vnd / 1_000 * POINTS_PER_1000_VND_PURCHASE)

    @staticmethod
    def calc_points_for_order(total_vnd: int) -> int:
        """Tính điểm khi đặt bánh kem."""
        return math.floor(total_vnd / 1_000 * POINTS_PER_1000_VND_ORDER)

    def _get_or_create_balance(self, user_id: str) -> dict:
        """Lấy bản ghi điểm của user, tạo mới nếu chưa có."""
        result = (
            self._db.table("loyalty_points")
            .select("user_id, points, total_earned, updated_at")
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        if result and result.data:
            return result.data

        # Tạo mới bản ghi với 0 điểm
        insert_result = (
            self._db.table("loyalty_points")
            .insert({"user_id": user_id, "points": 0, "total_earned": 0})
            .execute()
        )
        return insert_result.data[0] if insert_result.data else {"user_id": user_id, "points": 0, "total_earned": 0}

    # ── Public API ───────────────────────────────────────────────────────────

    def get_balance(self, user_id: str) -> dict:
        """
        Lấy số dư điểm + thông tin tổng quát.

        Returns:
            dict với keys: points, total_earned, next_milestone, points_to_next
        """
        balance = self._get_or_create_balance(user_id)
        current = balance["points"]

        # Tính mốc đổi điểm tiếp theo
        redeemed_so_far = current // REDEEM_POINTS_PER_VOUCHER * REDEEM_POINTS_PER_VOUCHER
        points_to_next = REDEEM_POINTS_PER_VOUCHER - (current % REDEEM_POINTS_PER_VOUCHER)
        if points_to_next == REDEEM_POINTS_PER_VOUCHER:
            points_to_next = 0  # đang đúng mốc, có thể đổi ngay

        return {
            "points": current,
            "total_earned": balance["total_earned"],
            "voucher_value": REDEEM_VALUE_PER_VOUCHER,
            "points_per_voucher": REDEEM_POINTS_PER_VOUCHER,
            "available_vouchers": current // REDEEM_POINTS_PER_VOUCHER,
            "points_to_next_voucher": points_to_next,
            "updated_at": balance.get("updated_at"),
        }

    def get_transactions(self, user_id: str, limit: int = 20) -> list[dict]:
        """Lấy lịch sử giao dịch điểm gần nhất."""
        result = (
            self._db.table("loyalty_transactions")
            .select("id, points, type, ref_id, note, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []

    def award_points(
        self,
        user_id: str,
        amount_vnd: int,
        source_type: str,   # 'purchase' | 'order'
        ref_id: str,
        note: str | None = None,
    ) -> int:
        """
        Cộng điểm cho user sau khi hoàn thành giao dịch.

        Args:
            user_id:     UUID của khách hàng
            amount_vnd:  Số tiền giao dịch (VND)
            source_type: 'purchase' (bánh ngọt) hoặc 'order' (bánh kem)
            ref_id:      ID của purchase/order
            note:        Mô tả tùy chọn

        Returns:
            Số điểm đã cộng
        """
        if source_type == "purchase":
            pts = self.calc_points_for_purchase(amount_vnd)
        elif source_type == "order":
            pts = self.calc_points_for_order(amount_vnd)
        else:
            raise LoyaltyServiceError(f"Loại giao dịch không hợp lệ: {source_type}")

        if pts <= 0:
            return 0

        try:
            # Đảm bảo bản ghi tồn tại
            self._get_or_create_balance(user_id)

            # Cộng điểm vào bảng loyalty_points bằng raw SQL update
            self._db.rpc(
                "increment_loyalty_points",
                {"p_user_id": user_id, "p_points": pts},
            ).execute()
        except Exception:
            # Fallback: dùng select + update thủ công nếu RPC chưa tồn tại
            current = self._get_or_create_balance(user_id)
            new_points = current["points"] + pts
            new_total  = current["total_earned"] + pts
            (
                self._db.table("loyalty_points")
                .update({"points": new_points, "total_earned": new_total, "updated_at": "now()"})
                .eq("user_id", user_id)
                .execute()
            )

        # Ghi lịch sử
        if not note:
            if source_type == "purchase":
                note = f"Mua bánh ngọt — {amount_vnd:,} VND"
            else:
                note = f"Đặt bánh kem — {amount_vnd:,} VND"

        try:
            self._db.table("loyalty_transactions").insert({
                "user_id":  user_id,
                "points":   pts,
                "type":     source_type,
                "ref_id":   ref_id,
                "note":     note,
            }).execute()
        except Exception as e:
            _logger.warning("Không ghi được loyalty_transaction (user=%s): %s", user_id, e)

        _logger.info("Đã cộng %d điểm cho user %s (type=%s, ref=%s)", pts, user_id, source_type, ref_id)
        return pts

    def redeem_points(self, user_id: str, voucher_count: int) -> dict:
        """
        Đổi điểm lấy voucher giảm giá.

        Args:
            user_id:       UUID của khách hàng
            voucher_count: Số voucher muốn đổi (mỗi voucher = 100 điểm = 5,000 VND)

        Returns:
            dict: discount_vnd, points_used, remaining_points, voucher_codes
        """
        if voucher_count < 1:
            raise LoyaltyServiceError("Số voucher phải ít nhất là 1.")

        points_needed = voucher_count * REDEEM_POINTS_PER_VOUCHER

        if points_needed > MAX_REDEEM_AT_ONCE:
            raise LoyaltyServiceError(
                f"Tối đa đổi {MAX_REDEEM_AT_ONCE // REDEEM_POINTS_PER_VOUCHER} voucher một lần."
            )

        balance = self._get_or_create_balance(user_id)
        if balance["points"] < points_needed:
            raise InsufficientPointsError(balance["points"], points_needed)

        # Trừ điểm
        new_points = balance["points"] - points_needed
        self._db.table("loyalty_points").update({
            "points": new_points,
            "updated_at": "now()",
        }).eq("user_id", user_id).execute()

        # Tạo voucher codes đơn giản: BONOBONO-<timestamp>-<seq>
        import time
        ts = int(time.time())
        voucher_codes = [
            f"BONOBONO-{ts}-{i+1}" for i in range(voucher_count)
        ]

        discount_vnd = voucher_count * REDEEM_VALUE_PER_VOUCHER

        # Ghi lịch sử
        note = f"Đổi {points_needed} điểm lấy {voucher_count} voucher giảm {discount_vnd:,} VND"
        self._db.table("loyalty_transactions").insert({
            "user_id": user_id,
            "points":  -points_needed,
            "type":    "redeem",
            "ref_id":  voucher_codes[0],
            "note":    note,
        }).execute()

        return {
            "voucher_codes": voucher_codes,
            "discount_vnd": discount_vnd,
            "points_used": points_needed,
            "remaining_points": new_points,
            "message": f"Đổi thành công! Bạn nhận được {voucher_count} voucher giảm {discount_vnd:,} VND.",
        }
