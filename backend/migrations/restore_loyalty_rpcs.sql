-- Restore the loyalty RPCs used by the FastAPI backend.
-- The loyalty tables already exist, but these functions were not deployed.

CREATE UNIQUE INDEX IF NOT EXISTS idx_loyalty_transactions_unique_ref
ON public.loyalty_transactions (user_id, type, ref_id);

CREATE OR REPLACE FUNCTION public.increment_loyalty_points(
    p_user_id UUID,
    p_points INTEGER,
    p_type TEXT,
    p_ref_id TEXT,
    p_note TEXT
)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_new_points INTEGER;
BEGIN
    INSERT INTO public.loyalty_transactions (user_id, points, type, ref_id, note)
    VALUES (p_user_id, p_points, p_type, p_ref_id, p_note)
    ON CONFLICT (user_id, type, ref_id) DO NOTHING;

    IF FOUND THEN
        INSERT INTO public.loyalty_points (user_id, points, total_earned, updated_at)
        VALUES (p_user_id, p_points, p_points, now())
        ON CONFLICT (user_id) DO UPDATE
            SET points = public.loyalty_points.points + EXCLUDED.points,
                total_earned = public.loyalty_points.total_earned + EXCLUDED.points,
                updated_at = now()
        RETURNING points INTO v_new_points;
    ELSE
        SELECT points
        INTO v_new_points
        FROM public.loyalty_points
        WHERE user_id = p_user_id;
    END IF;

    RETURN v_new_points;
END;
$$;

REVOKE EXECUTE ON FUNCTION public.increment_loyalty_points(UUID, INTEGER, TEXT, TEXT, TEXT) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.increment_loyalty_points(UUID, INTEGER, TEXT, TEXT, TEXT) FROM anon;
REVOKE EXECUTE ON FUNCTION public.increment_loyalty_points(UUID, INTEGER, TEXT, TEXT, TEXT) FROM authenticated;
GRANT EXECUTE ON FUNCTION public.increment_loyalty_points(UUID, INTEGER, TEXT, TEXT, TEXT) TO service_role;

CREATE OR REPLACE FUNCTION public.rpc_redeem_points(
    p_user_id UUID,
    p_points_needed INTEGER,
    p_voucher_codes TEXT[],
    p_voucher_value INTEGER,
    p_note TEXT
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
    UPDATE public.loyalty_points
    SET points = points - p_points_needed,
        updated_at = now()
    WHERE user_id = p_user_id
      AND points >= p_points_needed
    RETURNING points INTO v_remaining;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'INSUFFICIENT_POINTS'
            USING ERRCODE = 'P0001';
    END IF;

    INSERT INTO public.loyalty_transactions (user_id, points, type, ref_id, note)
    VALUES (p_user_id, -p_points_needed, 'redeem', p_voucher_codes[1], p_note)
    RETURNING id INTO v_tx_id;

    FOREACH v_code IN ARRAY p_voucher_codes
    LOOP
        INSERT INTO public.vouchers (code, user_id, discount_vnd, status, transaction_id)
        VALUES (v_code, p_user_id, p_voucher_value, 'active', v_tx_id);
    END LOOP;

    RETURN QUERY SELECT v_remaining;
END;
$$;

REVOKE EXECUTE ON FUNCTION public.rpc_redeem_points(UUID, INTEGER, TEXT[], INTEGER, TEXT) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.rpc_redeem_points(UUID, INTEGER, TEXT[], INTEGER, TEXT) FROM anon;
REVOKE EXECUTE ON FUNCTION public.rpc_redeem_points(UUID, INTEGER, TEXT[], INTEGER, TEXT) FROM authenticated;
GRANT EXECUTE ON FUNCTION public.rpc_redeem_points(UUID, INTEGER, TEXT[], INTEGER, TEXT) TO service_role;

-- Backfill completed transactions missed while increment_loyalty_points was absent.
SELECT public.increment_loyalty_points(
    p.customer_id,
    floor(p.total_price::numeric / 1000)::integer,
    'purchase',
    p.id::text,
    'Mua banh ngot - ' || p.total_price::text || ' VND'
)
FROM public.purchases AS p
WHERE p.status = 'completed'
  AND p.customer_id IS NOT NULL
  AND p.created_at >= timestamptz '2026-06-12 00:00:00+00'
  AND NOT EXISTS (
      SELECT 1
      FROM public.loyalty_transactions AS lt
      WHERE lt.user_id = p.customer_id
        AND lt.type = 'purchase'
        AND lt.ref_id = p.id::text
  );

SELECT public.increment_loyalty_points(
    o.customer_id,
    floor(o.total_price::numeric / 1000 * 1.5)::integer,
    'order',
    o.id::text,
    'Dat banh kem - ' || o.total_price::text || ' VND'
)
FROM public.orders AS o
WHERE o.status = 'delivered'
  AND o.customer_id IS NOT NULL
  AND o.updated_at >= timestamptz '2026-06-12 00:00:00+00'
  AND NOT EXISTS (
      SELECT 1
      FROM public.loyalty_transactions AS lt
      WHERE lt.user_id = o.customer_id
        AND lt.type = 'order'
        AND lt.ref_id = o.id::text
  );

NOTIFY pgrst, 'reload schema';
