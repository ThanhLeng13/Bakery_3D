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

-- ─── 3. Bảng vouchers (Mã giảm giá) ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS vouchers (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    code            TEXT        NOT NULL UNIQUE,
    user_id         UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    discount_vnd    INTEGER     NOT NULL,
    status          TEXT        NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'used', 'expired')),
    transaction_id  UUID        REFERENCES loyalty_transactions(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    used_at         TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ
);

-- ─── 4. Indexes & Constraints ──────────────────────────────────────────────────
-- Ràng buộc tránh cộng điểm 2 lần cho cùng 1 giao dịch
ALTER TABLE loyalty_transactions 
    ADD CONSTRAINT unique_user_type_ref UNIQUE (user_id, type, ref_id);

CREATE INDEX IF NOT EXISTS idx_loyalty_transactions_user_id
    ON loyalty_transactions(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_vouchers_code
    ON vouchers(code);

CREATE INDEX IF NOT EXISTS idx_vouchers_user_id
    ON vouchers(user_id, created_at DESC);

-- ─── 5. Row Level Security ────────────────────────────────────────────────────
ALTER TABLE loyalty_points       ENABLE ROW LEVEL SECURITY;
ALTER TABLE loyalty_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE vouchers             ENABLE ROW LEVEL SECURITY;

-- Khách hàng chỉ đọc dữ liệu của chính mình
CREATE POLICY "Customer can view own loyalty_points"
    ON loyalty_points FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Customer can view own loyalty_transactions"
    ON loyalty_transactions FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Customer can view own vouchers"
    ON vouchers FOR SELECT
    USING (auth.uid() = user_id);

-- Service role (backend) được phép ghi (INSERT/UPDATE) — bypass RLS
-- (service_role key vốn bypass RLS, policy này chỉ rõ ý định)

-- ─── 5. RPC: increment_loyalty_points ────────────────────────────────────────
-- Cộng điểm atomically (upsert) và ghi lịch sử (idempotent).
-- Dùng INSERT ... ON CONFLICT DO NOTHING cho transaction, nếu thành công mới cộng điểm.
-- SECURITY DEFINER + pinned search_path: ngăn search_path injection attack.
CREATE OR REPLACE FUNCTION increment_loyalty_points(
    p_user_id  UUID,
    p_points   INTEGER,
    p_type     TEXT,
    p_ref_id   TEXT,
    p_note     TEXT
)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_new_points INTEGER;
BEGIN
    -- Ghi lịch sử trước, bỏ qua nếu đã tồn tại (dựa vào unique constraint)
    INSERT INTO public.loyalty_transactions (user_id, points, type, ref_id, note)
    VALUES (p_user_id, p_points, p_type, p_ref_id, p_note)
    ON CONFLICT (user_id, type, ref_id) DO NOTHING;

    -- Nếu insert thành công (tức là giao dịch mới)
    IF FOUND THEN
        INSERT INTO public.loyalty_points (user_id, points, total_earned, updated_at)
        VALUES (p_user_id, p_points, p_points, now())
        ON CONFLICT (user_id) DO UPDATE
            SET points       = public.loyalty_points.points + EXCLUDED.points,
                total_earned = public.loyalty_points.total_earned + EXCLUDED.points,
                updated_at   = now()
        RETURNING points INTO v_new_points;
    ELSE
        -- Nếu giao dịch đã tồn tại, trả về điểm hiện tại
        SELECT points INTO v_new_points FROM public.loyalty_points WHERE user_id = p_user_id;
    END IF;

    RETURN v_new_points;
END;
$$;

-- Revoke broad access first; chỉ service_role (backend) được gọi RPC này.
REVOKE EXECUTE ON FUNCTION increment_loyalty_points(UUID, INTEGER, TEXT, TEXT, TEXT) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION increment_loyalty_points(UUID, INTEGER, TEXT, TEXT, TEXT) FROM anon;
REVOKE EXECUTE ON FUNCTION increment_loyalty_points(UUID, INTEGER, TEXT, TEXT, TEXT) FROM authenticated;
GRANT  EXECUTE ON FUNCTION increment_loyalty_points(UUID, INTEGER, TEXT, TEXT, TEXT) TO   service_role;

-- ─── 6. RPC: rpc_redeem_points ────────────────────────────────────────────────
-- Trừ điểm + ghi lịch sử + sinh vouchers trong một transaction duy nhất.
-- Atomic check-and-decrement: loại bỏ race condition double-spending.
-- Raise SQLSTATE P0001 'INSUFFICIENT_POINTS' nếu không đủ điểm.
-- SECURITY DEFINER + pinned search_path: ngăn search_path injection attack.
CREATE OR REPLACE FUNCTION rpc_redeem_points(
    p_user_id       UUID,
    p_points_needed INTEGER,
    p_voucher_codes TEXT[],
    p_note          TEXT
)
RETURNS TABLE(remaining_points INTEGER)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_remaining INTEGER;
    v_tx_id UUID;
    v_code TEXT;
BEGIN
    -- Atomic: UPDATE chỉ xảy ra khi points >= p_points_needed
    UPDATE public.loyalty_points
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

    -- Ghi lịch sử trong cùng transaction, lấy ID trả về
    INSERT INTO public.loyalty_transactions (user_id, points, type, ref_id, note)
    VALUES (p_user_id, -p_points_needed, 'redeem', p_voucher_codes[1], p_note)
    RETURNING id INTO v_tx_id;

    -- Ghi tất cả voucher codes liên kết với transaction_id
    FOREACH v_code IN ARRAY p_voucher_codes
    LOOP
        INSERT INTO public.vouchers (code, user_id, discount_vnd, status, transaction_id)
        VALUES (v_code, p_user_id, 5000, 'active', v_tx_id);
    END LOOP;

    RETURN QUERY SELECT v_remaining;
END;
$$;

-- Revoke broad access first; chỉ service_role (backend) được gọi RPC này.
REVOKE EXECUTE ON FUNCTION rpc_redeem_points(UUID, INTEGER, TEXT[], TEXT) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION rpc_redeem_points(UUID, INTEGER, TEXT[], TEXT) FROM anon;
REVOKE EXECUTE ON FUNCTION rpc_redeem_points(UUID, INTEGER, TEXT[], TEXT) FROM authenticated;
GRANT  EXECUTE ON FUNCTION rpc_redeem_points(UUID, INTEGER, TEXT[], TEXT) TO   service_role;
