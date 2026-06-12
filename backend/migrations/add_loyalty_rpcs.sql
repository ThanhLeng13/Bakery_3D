-- Migration: Thêm các hàm RPC cho hệ thống tích điểm
-- Created: 2026-06-12

-- ─── RPC 1: increment_loyalty_points ─────────────────────────────────────────
-- Cộng điểm atomically bằng INSERT ... ON CONFLICT DO UPDATE.
-- SECURITY DEFINER + SET search_path: ngăn search_path injection.
CREATE OR REPLACE FUNCTION increment_loyalty_points(
    p_user_id  UUID,
    p_points   INTEGER
)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_new_points INTEGER;
BEGIN
    INSERT INTO public.loyalty_points (user_id, points, total_earned, updated_at)
    VALUES (p_user_id, p_points, p_points, now())
    ON CONFLICT (user_id) DO UPDATE
        SET points       = public.loyalty_points.points + EXCLUDED.points,
            total_earned = public.loyalty_points.total_earned + EXCLUDED.points,
            updated_at   = now()
    RETURNING points INTO v_new_points;

    RETURN v_new_points;
END;
$$;

REVOKE EXECUTE ON FUNCTION increment_loyalty_points(UUID, INTEGER) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION increment_loyalty_points(UUID, INTEGER) FROM anon;
REVOKE EXECUTE ON FUNCTION increment_loyalty_points(UUID, INTEGER) FROM authenticated;
GRANT  EXECUTE ON FUNCTION increment_loyalty_points(UUID, INTEGER) TO   service_role;

-- ─── RPC 2: rpc_redeem_points ─────────────────────────────────────────────────
-- Trừ điểm + ghi lịch sử trong một transaction duy nhất.
-- SECURITY DEFINER + SET search_path: ngăn search_path injection.
CREATE OR REPLACE FUNCTION rpc_redeem_points(
    p_user_id       UUID,
    p_points_needed INTEGER,
    p_ref_id        TEXT,
    p_note          TEXT
)
RETURNS TABLE(remaining_points INTEGER)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_remaining INTEGER;
BEGIN
    UPDATE public.loyalty_points
    SET points     = points - p_points_needed,
        updated_at = now()
    WHERE user_id = p_user_id
      AND points  >= p_points_needed
    RETURNING points INTO v_remaining;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'INSUFFICIENT_POINTS'
            USING ERRCODE = 'P0001';
    END IF;

    INSERT INTO public.loyalty_transactions (user_id, points, type, ref_id, note)
    VALUES (p_user_id, -p_points_needed, 'redeem', p_ref_id, p_note);

    RETURN QUERY SELECT v_remaining;
END;
$$;

REVOKE EXECUTE ON FUNCTION rpc_redeem_points(UUID, INTEGER, TEXT, TEXT) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION rpc_redeem_points(UUID, INTEGER, TEXT, TEXT) FROM anon;
REVOKE EXECUTE ON FUNCTION rpc_redeem_points(UUID, INTEGER, TEXT, TEXT) FROM authenticated;
GRANT  EXECUTE ON FUNCTION rpc_redeem_points(UUID, INTEGER, TEXT, TEXT) TO   service_role;
