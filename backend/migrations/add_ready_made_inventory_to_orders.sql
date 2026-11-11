-- Track the branch for catalogue orders and consume ready-made stock atomically.
--
-- This migration extends the existing rpc_create_order contract. It is safe to
-- run after add_create_order_rpc.sql and add_order_voucher_columns.sql.
--
-- Business rule:
--   * A catalogue item (item.product_id is non-empty) is a ready-made item.
--     It must have a branch and its product_batches stock is consumed FIFO.
--   * A custom Studio item uses the nil/empty product_id and keeps the old
--     24/48-hour made-to-order rule; it does not consume product_batches.
--   * The stock check and decrement happen in the SAME transaction as orders,
--     order_items and history. A concurrent order waits on FOR UPDATE and then
--     sees the reduced quantity, so it cannot oversell the last cake.
--
-- Existing orders remain valid: branch_id is nullable for historical orders and
-- custom orders. New ready-made catalogue orders pass p_branch_id.

ALTER TABLE public.orders
    ADD COLUMN IF NOT EXISTS branch_id UUID REFERENCES public.branches(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_orders_branch_id ON public.orders(branch_id);

-- PostgreSQL xem số lượng/kiểu tham số là định danh của function. Chỉ dùng
-- CREATE OR REPLACE với thêm p_branch_id sẽ tạo overload 13 tham số, còn hàm
-- 12 tham số cũ vẫn tồn tại. Xoá đúng chữ ký cũ trước để PostgREST không mơ hồ
-- và mọi cuộc gọi buộc đi qua hợp đồng có chi nhánh mới.
DROP FUNCTION IF EXISTS public.rpc_create_order(
    UUID, TEXT, TEXT, TEXT, TIMESTAMPTZ, INTEGER, TEXT, TEXT, INTEGER,
    JSONB, JSONB, TEXT
);

CREATE FUNCTION public.rpc_create_order(
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
    p_idempotency_key TEXT,
    p_branch_id UUID DEFAULT NULL
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
    v_product_id UUID;
    v_quantity INTEGER;
    v_subtotal INTEGER;
    v_discount INTEGER;
    v_total INTEGER;
    v_claimed BOOLEAN := FALSE;
    v_status TEXT;
    v_voucher_code TEXT;
    v_voucher_id UUID;
    v_batch RECORD;
    v_remaining INTEGER;
    v_take INTEGER;
    v_has_catalogue_item BOOLEAN := FALSE;
BEGIN
    IF p_idempotency_key IS NOT NULL THEN
        INSERT INTO public.order_idempotency (customer_id, idempotency_key)
        VALUES (p_customer_id, p_idempotency_key)
        ON CONFLICT (customer_id, idempotency_key) DO NOTHING
        RETURNING TRUE INTO v_claimed;

        IF v_claimed IS DISTINCT FROM TRUE THEN
            SELECT oi.order_id INTO v_order_id
            FROM public.order_idempotency oi
            WHERE oi.customer_id = p_customer_id
              AND oi.idempotency_key = p_idempotency_key;

            IF v_order_id IS NOT NULL THEN
                SELECT o.total_price, o.voucher_discount, o.status
                INTO v_total, v_discount, v_status
                FROM public.orders o WHERE o.id = v_order_id;
                v_discount := COALESCE(v_discount, 0);
                v_subtotal := v_total + v_discount;
                SELECT o.voucher_code INTO v_voucher_code
                FROM public.orders o WHERE o.id = v_order_id;
                RETURN QUERY SELECT v_order_id, v_subtotal, v_discount,
                    v_total, TRUE, v_status, v_voucher_code;
                RETURN;
            END IF;

            RAISE EXCEPTION 'Đơn hàng trùng đang được tạo, vui lòng thử lại.'
                USING ERRCODE = 'serialization_failure';
        END IF;
    END IF;

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

    -- A non-empty product_id means the customer selected a ready-made
    -- catalogue item. Validate the branch before inserting the order.
    FOR v_item IN SELECT * FROM jsonb_array_elements(COALESCE(p_items, '[]'::jsonb))
    LOOP
        IF NULLIF(v_item->>'product_id', '') IS NOT NULL THEN
            v_has_catalogue_item := TRUE;
            EXIT;
        END IF;
    END LOOP;

    IF v_has_catalogue_item AND p_branch_id IS NULL THEN
        RAISE EXCEPTION 'Mẫu có sẵn cần chọn chi nhánh nhận bánh.'
            USING ERRCODE = 'check_violation';
    END IF;

    IF v_has_catalogue_item THEN
        PERFORM 1 FROM public.branches
        WHERE id = p_branch_id AND is_active = TRUE;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'Chi nhánh nhận bánh không tồn tại hoặc không hoạt động.'
                USING ERRCODE = 'foreign_key_violation';
        END IF;

        -- Consume each catalogue product FIFO. FOR UPDATE serializes two
        -- orders trying to take the same remaining cake.
        FOR v_item IN SELECT * FROM jsonb_array_elements(COALESCE(p_items, '[]'::jsonb))
        LOOP
            v_product_id := NULLIF(v_item->>'product_id', '')::uuid;
            IF v_product_id IS NULL THEN
                CONTINUE;
            END IF;

            v_remaining := (v_item->>'quantity')::integer;
            FOR v_batch IN
                SELECT id, quantity, quantity_sold
                FROM public.product_batches
                WHERE product_id = v_product_id
                  AND branch_id = p_branch_id
                  AND is_active = TRUE
                  AND expires_at >= CURRENT_DATE
                  AND quantity_sold < quantity
                ORDER BY expires_at ASC, produced_at ASC, id ASC
                FOR UPDATE
            LOOP
                EXIT WHEN v_remaining <= 0;
                v_take := LEAST(v_remaining, v_batch.quantity - v_batch.quantity_sold);
                UPDATE public.product_batches
                SET quantity_sold = quantity_sold + v_take,
                    updated_at = now()
                WHERE id = v_batch.id;
                v_remaining := v_remaining - v_take;
            END LOOP;

            IF v_remaining > 0 THEN
                RAISE EXCEPTION 'Mẫu bánh tại chi nhánh không còn đủ số lượng.'
                    USING ERRCODE = 'serialization_failure';
            END IF;
        END LOOP;
    END IF;

    INSERT INTO public.orders (
        customer_id, branch_id, status, total_price, pickup_date,
        customer_name, customer_phone, customer_email, ai_summary,
        voucher_code, voucher_discount
    )
    VALUES (
        p_customer_id, p_branch_id, 'pending', p_total_price, p_pickup_date,
        p_full_name, p_phone, p_email, p_ai_summary,
        p_voucher_code, COALESCE(p_voucher_discount, 0)
    )
    RETURNING id INTO v_order_id;

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
            VALUES (v_order_id, v_item_id, v_item->'customization_json');
        END IF;
    END LOOP;

    INSERT INTO public.order_status_history (
        order_id, old_status, new_status, changed_by
    ) VALUES (v_order_id, NULL, 'pending', p_customer_id);

    IF p_idempotency_key IS NOT NULL THEN
        UPDATE public.order_idempotency
        SET order_id = v_order_id
        WHERE customer_id = p_customer_id
          AND idempotency_key = p_idempotency_key;
    END IF;

    v_subtotal := p_total_price + COALESCE(p_voucher_discount, 0);
    v_discount := COALESCE(p_voucher_discount, 0);
    v_total := p_total_price;

    RETURN QUERY SELECT v_order_id, v_subtotal, v_discount, v_total,
        v_duplicate, 'pending'::TEXT, p_voucher_code;
END;
$$;

REVOKE EXECUTE ON FUNCTION public.rpc_create_order(UUID, TEXT, TEXT, TEXT, TIMESTAMPTZ, INTEGER, TEXT, TEXT, INTEGER, JSONB, JSONB, TEXT, UUID) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.rpc_create_order(UUID, TEXT, TEXT, TEXT, TIMESTAMPTZ, INTEGER, TEXT, TEXT, INTEGER, JSONB, JSONB, TEXT, UUID) FROM anon;
REVOKE EXECUTE ON FUNCTION public.rpc_create_order(UUID, TEXT, TEXT, TEXT, TIMESTAMPTZ, INTEGER, TEXT, TEXT, INTEGER, JSONB, JSONB, TEXT, UUID) FROM authenticated;
GRANT EXECUTE ON FUNCTION public.rpc_create_order(UUID, TEXT, TEXT, TEXT, TIMESTAMPTZ, INTEGER, TEXT, TEXT, INTEGER, JSONB, JSONB, TEXT, UUID) TO service_role;

NOTIFY pgrst, 'reload schema';
-- End of migration.
