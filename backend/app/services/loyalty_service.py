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
import secrets
from datetime import datetime, timezone
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
        """Lấy bản ghi điểm của user, tạo mới nếu chưa có.

        An toàn với concurrent calls: nếu INSERT bị UniqueViolation do tiến trình
        song song đã tạo trước, sẽ SELECT lại bản ghi đó thay vì raise lỗi.
        """
        result = (
            self._db.table("loyalty_points")
            .select("user_id, points, total_earned, updated_at")
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        if result and result.data:
            return result.data

        # Tạo mới bản ghi với 0 điểm.
        # Nếu bị UniqueViolation (tiến trình song song đã INSERT trước), SELECT lại.
        try:
            insert_result = (
                self._db.table("loyalty_points")
                .insert({"user_id": user_id, "points": 0, "total_earned": 0})
                .execute()
            )
            return insert_result.data[0] if insert_result.data else {"user_id": user_id, "points": 0, "total_earned": 0}
        except Exception as insert_exc:
            exc_str = str(insert_exc)
            # 23505 = unique_violation (PK conflict from concurrent insert)
            if "23505" in exc_str or "unique" in exc_str.lower() or "duplicate" in exc_str.lower():
                _logger.debug("_get_or_create_balance: concurrent INSERT detected for user=%s, re-querying", user_id)
                retry = (
                    self._db.table("loyalty_points")
                    .select("user_id, points, total_earned, updated_at")
                    .eq("user_id", user_id)
                    .maybe_single()
                    .execute()
                )
                if retry and retry.data:
                    return retry.data
            raise

    # ── Public API ───────────────────────────────────────────────────────────

    def get_balance(self, user_id: str) -> dict:
        """
        Lấy số dư điểm + thông tin tổng quát.

        Returns:
            dict với keys: points, total_earned, next_milestone, points_to_next
        """
        balance = self._get_or_create_balance(user_id)
        current = balance["points"]

        # Tính số điểm còn thiếu đến mốc voucher tiếp theo.
        # - current == 0  → points_to_next = 100 (chưa đủ điểm để đổi)
        # - current đúng mốc (và > 0) → points_to_next = 0 (có thể đổi ngay)
        points_to_next = REDEEM_POINTS_PER_VOUCHER - (current % REDEEM_POINTS_PER_VOUCHER)
        if points_to_next == REDEEM_POINTS_PER_VOUCHER and current > 0:
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

        Ưu tiên dùng RPC `increment_loyalty_points` (atomic upsert).
        Fallback về read-modify-write nếu RPC chưa khả dụng.

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

        if not note:
            if source_type == "purchase":
                note = f"Mua bánh ngọt — {amount_vnd:,} VND"
            else:
                note = f"Đặt bánh kem — {amount_vnd:,} VND"

        # Atomic upsert via RPC + Idempotent history insertion
        # Gọi RPC để insert transaction (nếu chưa có) và cộng điểm trong một transaction DB.
        # RPC sẽ no-op (không cộng điểm 2 lần) nếu giao dịch đã tồn tại.
        try:
            self._db.rpc(
                "increment_loyalty_points",
                {
                    "p_user_id": user_id, 
                    "p_points": pts,
                    "p_type": source_type,
                    "p_ref_id": ref_id,
                    "p_note": note
                },
            ).execute()
        except Exception as rpc_exc:
            _logger.error(
                "Lỗi khi cộng điểm (user=%s, type=%s, ref=%s): %s",
                user_id, source_type, ref_id, rpc_exc
            )
            # Quăng lỗi để caller biết việc cộng điểm thất bại, không tự fallback 
            # để đảm bảo tính toàn vẹn (tránh double-spend).
            raise LoyaltyServiceError("Không thể cộng điểm do lỗi hệ thống.") from rpc_exc

        _logger.info("Đã cộng %d điểm cho user %s (type=%s, ref=%s)", pts, user_id, source_type, ref_id)
        return pts

    def redeem_points(self, user_id: str, voucher_count: int) -> dict:
        """
        Đổi điểm lấy voucher giảm giá — atomic via RPC `rpc_redeem_points`.

        Sử dụng RPC DB để thực hiện check-and-decrement trong một transaction
        duy nhất, loại bỏ race condition double-spending khi có request đồng thời.

        Tất cả voucher codes được lưu vào bảng `vouchers` để nhân viên có thể
        xác minh tính hợp lệ và tránh gian lận / mất mã.

        Args:
            user_id:       UUID của khách hàng
            voucher_count: Số voucher muốn đổi (mỗi voucher = 100 điểm = 5,000 VND)

        Returns:
            dict: discount_vnd, points_used, remaining_points, voucher_codes

        Raises:
            InsufficientPointsError: Nếu không đủ điểm (do DB RPC báo lỗi).
            LoyaltyServiceError: Nếu tham số không hợp lệ.
        """
        if voucher_count < 1:
            raise LoyaltyServiceError("Số voucher phải ít nhất là 1.")

        points_needed = voucher_count * REDEEM_POINTS_PER_VOUCHER

        if points_needed > MAX_REDEEM_AT_ONCE:
            raise LoyaltyServiceError(
                f"Tối đa đổi {MAX_REDEEM_AT_ONCE // REDEEM_POINTS_PER_VOUCHER} voucher một lần."
            )

        # Tạo voucher codes bảo mật — 64-bit entropy hex, không thể đoán được.
        voucher_codes = [
            f"BNB-{secrets.token_hex(8).upper()}" for _ in range(voucher_count)
        ]

        discount_vnd = voucher_count * REDEEM_VALUE_PER_VOUCHER
        note = f"Đổi {points_needed} điểm lấy {voucher_count} voucher giảm {discount_vnd:,} VND"

        # ── Atomic redeem via DB RPC ──────────────────────────────────────────
        # rpc_redeem_points thực hiện:
        # 1. Trừ điểm (sẽ lỗi P0001 nếu không đủ điểm)
        # 2. Ghi lịch sử giao dịch loyalty_transactions
        # 3. Lưu TẤT CẢ voucher codes vào bảng vouchers
        # Tất cả nằm trong một database transaction. Nếu có bất kỳ lỗi nào (như đứt
        # kết nối hoặc constraint violation), mọi thứ rollback 100%. Không có rủi ro
        # mất điểm mà không nhận được voucher.
        try:
            rpc_result = self._db.rpc("rpc_redeem_points", {
                "p_user_id":       user_id,
                "p_points_needed": points_needed,
                "p_voucher_codes": voucher_codes,
                "p_note":          note,
            }).execute()

            # rpc_redeem_points trả về SETOF với cột remaining_points
            rows = rpc_result.data or []
            remaining_points: int = rows[0]["remaining_points"] if rows else 0

        except Exception as exc:
            exc_str = str(exc)
            # P0001 / INSUFFICIENT_POINTS = không đủ điểm → raise lỗi mượt mà
            if "INSUFFICIENT_POINTS" in exc_str or "P0001" in exc_str:
                try:
                    bal = self._get_or_create_balance(user_id)
                    available = bal["points"]
                except Exception:
                    available = 0
                raise InsufficientPointsError(available, points_needed) from exc

            # Các lỗi khác (cả undefined_function do chưa chạy migration, 
            # lỗi constraint vouchers, hoặc network) đều quăng ra 500
            # Không dùng fallback Python để đảm bảo nguyên tắc 100% atomic DB-side.
            _logger.error("Lỗi RPC rpc_redeem_points (user=%s): %s", user_id, exc_str)
            raise LoyaltyServiceError("Hệ thống lỗi khi đổi điểm, vui lòng thử lại sau.") from exc

        return {
            "voucher_codes": voucher_codes,
            "discount_vnd": discount_vnd,
            "points_used": points_needed,
            "remaining_points": remaining_points,
            "message": f"Đổi thành công! Bạn nhận được {voucher_count} voucher giảm {discount_vnd:,} VND.",
        }

