-- Migration: Hệ thống tích điểm khách hàng (Loyalty Points)
-- Created: 2026-06-12
--
-- Quy tắc:
--   Mua bánh ngọt (purchases): 1 điểm / 1,000 VND (làm tròn xuống)
--   Đặt bánh kem (orders):     1.5 điểm / 1,000 VND (làm tròn xuống)
--   Đổi điểm:                  100 điểm = 5,000 VND giảm giá

-- ─── 1. Bảng số dư điểm mỗi khách hàng ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS loyalty_points (
    user_id       UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    points        INTEGER NOT NULL DEFAULT 0 CHECK (points >= 0),
    total_earned  INTEGER NOT NULL DEFAULT 0,   -- tổng điểm đã từng nhận (không trừ)
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ─── 2. Bảng lịch sử giao dịch điểm ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS loyalty_transactions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    points      INTEGER NOT NULL,           -- dương = cộng, âm = trừ (đổi điểm)
    type        TEXT NOT NULL               -- 'purchase' | 'order' | 'redeem'
                    CHECK (type IN ('purchase', 'order', 'redeem')),
    ref_id      TEXT,                       -- ID của purchase / order / voucher liên quan
    note        TEXT,                       -- mô tả tóm tắt
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ─── 3. Indexes ───────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_loyalty_transactions_user_id
    ON loyalty_transactions(user_id, created_at DESC);

-- ─── 4. Row Level Security ────────────────────────────────────────────────────
ALTER TABLE loyalty_points       ENABLE ROW LEVEL SECURITY;
ALTER TABLE loyalty_transactions ENABLE ROW LEVEL SECURITY;

-- Khách hàng chỉ đọc dữ liệu của chính mình
CREATE POLICY "Customer can view own loyalty_points"
    ON loyalty_points FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Customer can view own loyalty_transactions"
    ON loyalty_transactions FOR SELECT
    USING (auth.uid() = user_id);

-- Service role (backend) được phép ghi (INSERT/UPDATE) — bypass RLS
-- (service_role key vốn bypass RLS, policy này chỉ rõ ý định)

-- ─── 5. RPC: increment_loyalty_points ────────────────────────────────────────
-- Cộng điểm atomically (upsert).  Được gọi bởi LoyaltyService.award_points.
-- Dùng INSERT ... ON CONFLICT DO UPDATE nên thread-safe, không bị lost-update.
CREATE OR REPLACE FUNCTION increment_loyalty_points(
    p_user_id  UUID,
    p_points   INTEGER
)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_new_points INTEGER;
BEGIN
    INSERT INTO loyalty_points (user_id, points, total_earned, updated_at)
    VALUES (p_user_id, p_points, p_points, now())
    ON CONFLICT (user_id) DO UPDATE
        SET points       = loyalty_points.points + EXCLUDED.points,
            total_earned = loyalty_points.total_earned + EXCLUDED.points,
            updated_at   = now()
    RETURNING points INTO v_new_points;

    RETURN v_new_points;
END;
$$;

GRANT EXECUTE ON FUNCTION increment_loyalty_points(UUID, INTEGER) TO service_role;

-- ─── 6. RPC: rpc_redeem_points ────────────────────────────────────────────────
-- Trừ điểm + ghi lịch sử trong một transaction duy nhất.
-- Atomic check-and-decrement: loại bỏ race condition double-spending.
-- Raise SQLSTATE P0001 'INSUFFICIENT_POINTS' nếu không đủ điểm.
CREATE OR REPLACE FUNCTION rpc_redeem_points(
    p_user_id       UUID,
    p_points_needed INTEGER,
    p_ref_id        TEXT,
    p_note          TEXT
)
RETURNS TABLE(remaining_points INTEGER)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_remaining INTEGER;
BEGIN
    -- Atomic: UPDATE chỉ xảy ra khi points >= p_points_needed
    UPDATE loyalty_points
    SET points     = points - p_points_needed,
        updated_at = now()
    WHERE user_id = p_user_id
      AND points  >= p_points_needed
    RETURNING points INTO v_remaining;

    -- Không UPDATE được hàng nào → không đủ điểm
    IF NOT FOUND THEN
        RAISE EXCEPTION 'INSUFFICIENT_POINTS'
            USING ERRCODE = 'P0001';
    END IF;

    -- Ghi lịch sử trong cùng transaction
    INSERT INTO loyalty_transactions (user_id, points, type, ref_id, note)
    VALUES (p_user_id, -p_points_needed, 'redeem', p_ref_id, p_note);

    RETURN QUERY SELECT v_remaining;
END;
$$;

GRANT EXECUTE ON FUNCTION rpc_redeem_points(UUID, INTEGER, TEXT, TEXT) TO service_role;
