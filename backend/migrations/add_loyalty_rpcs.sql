-- Migration: Thêm các hàm RPC cho hệ thống tích điểm
-- Created: 2026-06-12

-- ─── RPC 1: increment_loyalty_points ─────────────────────────────────────────
-- Cộng điểm atomically bằng INSERT ... ON CONFLICT DO UPDATE.
-- Tránh lost-update race condition khi award_points bị gọi đồng thời.
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

-- ─── RPC 2: rpc_redeem_points ─────────────────────────────────────────────────
-- Trừ điểm + ghi lịch sử trong một transaction duy nhất.
-- Đảm bảo không bao giờ trừ quá số điểm khả dụng (atomic check-and-decrement).
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
    -- Atomic: UPDATE chỉ xảy ra nếu points >= p_points_needed
    UPDATE loyalty_points
    SET points     = points - p_points_needed,
        updated_at = now()
    WHERE user_id = p_user_id
      AND points  >= p_points_needed
    RETURNING points INTO v_remaining;

    -- Nếu không UPDATE được hàng nào → không đủ điểm
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
