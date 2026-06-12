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

        try:
            # Atomic upsert via RPC—không cần _get_or_create_balance trước
            self._db.rpc(
                "increment_loyalty_points",
                {"p_user_id": user_id, "p_points": pts},
            ).execute()
        except Exception as rpc_exc:
            exc_str = str(rpc_exc)
            # Chỉ fallback khi lỗi là "undefined function" (SQLSTATE 42883 / PGRST202).
            # Mọi lỗi khác (network, auth, data, …) → re-raise để tránh double-mutation.
            is_undefined = (
                "42883" in exc_str          # PostgreSQL undefined_function
                or "PGRST202" in exc_str    # PostgREST: function not found in schema cache
                or "Could not find the function" in exc_str
            )
            if not is_undefined:
                raise

            _logger.warning(
                "increment_loyalty_points RPC không tồn tại, dùng fallback (user=%s): %s",
                user_id, exc_str[:200],
            )
            # Fallback: dùng select + update thủ công.
            now_iso = datetime.now(timezone.utc).isoformat()
            current = self._get_or_create_balance(user_id)
            new_points = current["points"] + pts
            new_total  = current["total_earned"] + pts
            (
                self._db.table("loyalty_points")
                .update({"points": new_points, "total_earned": new_total, "updated_at": now_iso})
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

        # transaction_id sẽ được lấy sau khi insert loyalty_transactions (fallback path)
        # hoặc look up từ loyalty_transactions (RPC path) để link với vouchers.
        transaction_id: str | None = None

        # ── Atomic redeem via DB RPC ──────────────────────────────────────────
        # rpc_redeem_points thực hiện UPDATE ... WHERE points >= needed và INSERT
        # transaction trong cùng một transaction DB. Nếu không đủ điểm, DB raise
        # SQLSTATE P0001 'INSUFFICIENT_POINTS'.
        try:
            rpc_result = self._db.rpc("rpc_redeem_points", {
                "p_user_id":       user_id,
                "p_points_needed": points_needed,
                "p_ref_id":        voucher_codes[0],
                "p_note":          note,
            }).execute()

            # rpc_redeem_points trả về SETOF với cột remaining_points
            rows = rpc_result.data or []
            remaining_points: int = rows[0]["remaining_points"] if rows else 0

            # Lấy transaction_id vừa được INSERT bởi RPC để link vouchers
            try:
                tx_row = (
                    self._db.table("loyalty_transactions")
                    .select("id")
                    .eq("user_id", user_id)
                    .eq("type", "redeem")
                    .eq("ref_id", voucher_codes[0])
                    .order("created_at", desc=True)
                    .limit(1)
                    .maybe_single()
                    .execute()
                )
                if tx_row and tx_row.data:
                    transaction_id = tx_row.data["id"]
            except Exception as tx_err:
                _logger.debug("Không lấy được transaction_id sau RPC (user=%s): %s", user_id, tx_err)

        except Exception as exc:
            exc_str = str(exc)
            # P0001 / INSUFFICIENT_POINTS = không đủ điểm → raise ngay, không fallback
            if "INSUFFICIENT_POINTS" in exc_str or "P0001" in exc_str:
                try:
                    bal = self._get_or_create_balance(user_id)
                    available = bal["points"]
                except Exception:
                    available = 0
                raise InsufficientPointsError(available, points_needed) from exc

            # Chỉ fallback khi lỗi là "undefined function" (SQLSTATE 42883 / PGRST202).
            # Mọi lỗi khác (transient DB error, timeout, lock conflict, …) → re-raise
            # để tránh kích hoạt path non-atomic và gây double-spending.
            is_undefined = (
                "42883" in exc_str           # PostgreSQL undefined_function
                or "PGRST202" in exc_str     # PostgREST: function not in schema cache
                or "Could not find the function" in exc_str
            )
            if not is_undefined:
                raise

            _logger.warning(
                "rpc_redeem_points không tồn tại, dùng fallback non-atomic (user=%s): %s",
                user_id, exc_str[:200],
            )
            now_iso = datetime.now(timezone.utc).isoformat()
            balance = self._get_or_create_balance(user_id)
            if balance["points"] < points_needed:
                raise InsufficientPointsError(balance["points"], points_needed) from exc

            remaining_points = balance["points"] - points_needed
            self._db.table("loyalty_points").update({
                "points":     remaining_points,
                "updated_at": now_iso,
            }).eq("user_id", user_id).execute()

            tx_insert = self._db.table("loyalty_transactions").insert({
                "user_id": user_id,
                "points":  -points_needed,
                "type":    "redeem",
                "ref_id":  voucher_codes[0],
                "note":    note,
            }).execute()

            # Lấy transaction_id vừa INSERT (fallback path)
            if tx_insert.data:
                transaction_id = tx_insert.data[0].get("id")

        # ── Lưu TẤT CẢ voucher codes vào bảng vouchers ──────────────────────
        # Mỗi code được ghi riêng để nhân viên có thể xác minh tính hợp lệ.
        # Trước đây chỉ lưu voucher_codes[0] trong ref_id → các code còn lại bị mất.
        try:
            voucher_rows = [
                {
                    "code":         code,
                    "user_id":      user_id,
                    "discount_vnd": REDEEM_VALUE_PER_VOUCHER,
                    "status":       "active",
                    "transaction_id": transaction_id,
                }
                for code in voucher_codes
            ]
            self._db.table("vouchers").insert(voucher_rows).execute()
        except Exception as v_err:
            # Ghi vouchers thất bại không nên huỷ giao dịch đã thành công,
            # nhưng cần log để xử lý thủ công nếu cần.
            _logger.error(
                "Không ghi được vouchers sau khi redeem (user=%s, codes=%s): %s",
                user_id, voucher_codes, v_err,
            )

        return {
            "voucher_codes": voucher_codes,
            "discount_vnd": discount_vnd,
            "points_used": points_needed,
            "remaining_points": remaining_points,
            "message": f"Đổi thành công! Bạn nhận được {voucher_count} voucher giảm {discount_vnd:,} VND.",
        }

