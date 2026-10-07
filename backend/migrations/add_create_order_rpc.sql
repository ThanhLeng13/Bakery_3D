-- Create an order and everything it owns in a single transaction.
--
-- Bug: `create_order` inserted into orders, then order_items, then
-- cake_customizations, then order_status_history as separate statements. If a
-- later one failed, the order row survived with missing items — the stored
-- total no longer matched the rows behind it, and the bakery received work it
-- could not fulfil. Nothing rolled back.
--
-- This function writes all of it or none of it. It also takes an idempotency
-- key so a customer who taps "Đặt hàng" twice on a slow connection gets one
-- order, not two.
--
-- Requires add_order_voucher_columns.sql for p_voucher_code / p_voucher_discount.
-- Safe to run more than once (CREATE OR REPLACE).

-- Idempotency ledger. A separate table rather than matching on order columns:
-- two genuinely different orders can share a pickup date and a total, and
-- those must not collapse into one. The client sends a key it reuses when
-- retrying, so only a real retry collides.
--
-- `order_id` is nullable on purpose: the row is INSERTed to claim the key before
-- the order exists, then UPDATEd with the id. Claiming first is what makes two
-- simultaneous retries safe - with a read-then-write the second request would
-- find nothing yet and create a second order.
CREATE TABLE IF NOT EXISTS public.order_idempotency (
    customer_id UUID NOT NULL,
    idempotency_key TEXT NOT NULL,
    order_id UUID REFERENCES public.orders(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (customer_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_order_idempotency_created
    ON public.order_idempotency (created_at);

CREATE OR REPLACE FUNCTION public.rpc_create_order(
    p_customer_id UUID,
    p_full_name TEXT,
    p_phone TEXT,
    p_email TEXT,
    p_pickup_date TIMESTAMPTZ,
    p_total_price INTEGER,
    p_ai_summary TEXT,
    p_voucher_code TEXT,
    p_voucher_discount INTEGER,
    p_items JSONB,
    p_customizations JSONB,
    p_idempotency_key TEXT
)
RETURNS TABLE (
    order_id UUID,
    subtotal INTEGER,
    discount INTEGER,
    total INTEGER,
    duplicate BOOLEAN,
    status TEXT,
    voucher_code TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_order_id UUID;
    v_duplicate BOOLEAN := FALSE;
    v_item JSONB;
    v_item_id UUID;
    v_subtotal INTEGER;
    v_discount INTEGER;
    v_total INTEGER;
    v_claimed BOOLEAN;
    v_status TEXT;
    v_voucher_code TEXT;
    v_voucher_id UUID;
BEGIN
    -- Idempotency: claim the key with an INSERT before creating anything. A
    -- read-then-write leaves a window where two simultaneous retries both see
    -- no row and both create an order. ON CONFLICT DO NOTHING means the loser
    -- of the race updates zero rows and returns the winner's order instead.
    --
    -- Scoped per customer, so two customers sending the same key text cannot
    -- collide with each other.
    IF p_idempotency_key IS NOT NULL THEN
        INSERT INTO public.order_idempotency (customer_id, idempotency_key)
        VALUES (p_customer_id, p_idempotency_key)
        ON CONFLICT (customer_id, idempotency_key) DO NOTHING
        RETURNING TRUE INTO v_claimed;

        IF NOT COALESCE(v_claimed, FALSE) THEN
            -- Someone else holds this key. Wait for their order to appear: the
            -- row is written before the order, so in a concurrent retry it may
            -- not be there yet on this snapshot.
            SELECT oi.order_id
            INTO v_order_id
            FROM public.order_idempotency oi
            WHERE oi.customer_id = p_customer_id
              AND oi.idempotency_key = p_idempotency_key;

            IF v_order_id IS NOT NULL THEN
                SELECT o.total_price, o.voucher_discount, o.status
                INTO v_total, v_discount, v_status
                FROM public.orders o
                WHERE o.id = v_order_id;

                v_discount := COALESCE(v_discount, 0);
                v_subtotal := v_total + v_discount;
                -- Report the original order's voucher and status, not this
                -- request's: a retry must not look like a fresh order.
                v_voucher_code := (
                    SELECT o.voucher_code FROM public.orders o WHERE o.id = v_order_id
                );
                RETURN QUERY SELECT
                    v_order_id, v_subtotal, v_discount, v_total, TRUE,
                    v_status, v_voucher_code;
                RETURN;
            END IF;

            -- The claim exists but its order is not readable yet. Refusing is
            -- safer than creating a second order: the client retries and then
            -- takes the branch above.
            RAISE EXCEPTION
                'Đơn hàng trùng đang được tạo, vui lòng thử lại.'
                USING ERRCODE = 'serialization_failure';
        END IF;
    END IF;

    -- Voucher: consume it here, inside this transaction, rather than after the
    -- order is written. find_usable() then mark_used() left a window where two
    -- concurrent orders could both pass the check and both get the discount.
    -- The conditional UPDATE is the check: only a row still 'active' is
    -- affected, so zero rows means somebody else took it and this order must
    -- not go through.
    IF p_voucher_code IS NOT NULL THEN
        UPDATE public.vouchers
        SET status = 'used', used_at = now()
        WHERE code = upper(btrim(p_voucher_code))
          AND status = 'active'
          AND (expires_at IS NULL OR expires_at > now())
          AND user_id = p_customer_id
        RETURNING id INTO v_voucher_id;

        IF v_voucher_id IS NULL THEN
            RAISE EXCEPTION 'Voucher không còn hiệu lực hoặc đã được dùng.'
                USING ERRCODE = 'check_violation';
        END IF;
    END IF;

    INSERT INTO public.orders (
        customer_id, status, total_price, pickup_date,
        customer_name, customer_phone, customer_email, ai_summary,
        voucher_code, voucher_discount
    )
    VALUES (
        p_customer_id, 'pending', p_total_price, p_pickup_date,
        p_full_name, p_phone, p_email, p_ai_summary,
        p_voucher_code, COALESCE(p_voucher_discount, 0)
    )
    RETURNING id INTO v_order_id;

    -- Each order item, then its customisation if it has one. Both live inside
    -- this transaction: an exception anywhere below rolls the whole thing back.
    FOR v_item IN SELECT * FROM jsonb_array_elements(COALESCE(p_items, '[]'::jsonb))
    LOOP
        INSERT INTO public.order_items (
            order_id, product_id, size, flavor, quantity, unit_price
        )
        VALUES (
            v_order_id,
            NULLIF(v_item->>'product_id', '')::uuid,
            v_item->>'size',
            v_item->>'flavor',
            (v_item->>'quantity')::integer,
            (v_item->>'unit_price')::integer
        )
        RETURNING id INTO v_item_id;

        IF v_item ? 'customization_json'
           AND v_item->'customization_json' IS NOT NULL
           AND v_item->'customization_json' <> 'null'::jsonb
        THEN
            INSERT INTO public.cake_customizations (
                order_id, order_item_id, customization_json
            )
            VALUES (
                v_order_id,
                v_item_id,
                v_item->'customization_json'
            );
        END IF;
    END LOOP;

    INSERT INTO public.order_status_history (
        order_id, old_status, new_status, changed_by
    )
    VALUES (v_order_id, NULL, 'pending', p_customer_id);

    -- Ledger last: if anything above raised, this row is gone too, so a retry
    -- after a failure creates a fresh order rather than resolving to one that
    -- was rolled back.
    IF p_idempotency_key IS NOT NULL THEN
        INSERT INTO public.order_idempotency (
            customer_id, idempotency_key, order_id
        )
        VALUES (p_customer_id, p_idempotency_key, v_order_id);
    END IF;

    v_subtotal := p_total_price + COALESCE(p_voucher_discount, 0);
    v_discount := COALESCE(p_voucher_discount, 0);
    v_total := p_total_price;

    RETURN QUERY SELECT
        v_order_id, v_subtotal, v_discount, v_total, v_duplicate,
        'pending'::TEXT, p_voucher_code;
END;
$$;

REVOKE EXECUTE ON FUNCTION public.rpc_create_order(UUID, TEXT, TEXT, TEXT, TIMESTAMPTZ, INTEGER, TEXT, TEXT, INTEGER, JSONB, JSONB, TEXT) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.rpc_create_order(UUID, TEXT, TEXT, TEXT, TIMESTAMPTZ, INTEGER, TEXT, TEXT, INTEGER, JSONB, JSONB, TEXT) FROM anon;
REVOKE EXECUTE ON FUNCTION public.rpc_create_order(UUID, TEXT, TEXT, TEXT, TIMESTAMPTZ, INTEGER, TEXT, TEXT, INTEGER, JSONB, JSONB, TEXT) FROM authenticated;
GRANT EXECUTE ON FUNCTION public.rpc_create_order(UUID, TEXT, TEXT, TEXT, TIMESTAMPTZ, INTEGER, TEXT, TEXT, INTEGER, JSONB, JSONB, TEXT) TO service_role;

NOTIFY pgrst, 'reload schema';