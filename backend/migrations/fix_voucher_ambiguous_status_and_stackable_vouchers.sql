-- Sửa lỗi không đặt được đơn khi áp dụng voucher & hỗ trợ cộng dồn voucher.
--
-- Nguyên nhân gốc đo được trên Postgres logs:
--   1. `rpc_create_order` khai báo `RETURNS TABLE (..., status TEXT, voucher_code TEXT)`,
--      tạo ra biến OUT tên `status`. Bên trong hàm, câu lệnh
--        UPDATE public.vouchers SET status = 'used' ... WHERE ... AND status = 'active'
--      không gắn alias cho bảng `vouchers`, nên Postgres báo:
--        ERROR 42702: column reference "status" is ambiguous
--      Kết quả: đặt đơn không voucher (bỏ qua nhánh IF) chạy bình thường cho cả
--      bánh sẵn lẫn bánh thiết kế 3D, nhưng cứ gắn voucher là lỗi 500.
--   2. Constraint `purchases_voucher_discount_check` kiểm tra `voucher_discount <= total_price`,
--      trong khi `total_price` là tiền SAU giảm (`subtotal - voucher_discount`). Khi khách
--      đổi voucher giá trị lớn (ví dụ giảm 40.000đ trên đơn 50.000đ -> total_price = 10.000đ),
--      lệnh INSERT bị Postgres từ chối.
--   3. Bổ sung `rpc_merge_vouchers` để khách có sẵn nhiều voucher 5.000đ trước đây
--      có thể gộp thành 1 voucher giá trị lớn dùng cho một đơn.

-- ─── 1. Fix rpc_create_order: qualify table aliases everywhere ──────────────

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
    p_idempotency_key TEXT,
    p_branch_id UUID DEFAULT NULL,
    p_customer_message TEXT DEFAULT NULL,
    p_fulfillment_type TEXT DEFAULT 'pickup',
    p_delivery_address TEXT DEFAULT NULL
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
    v_fulfillment TEXT;
    v_address TEXT;
BEGIN
    v_fulfillment := COALESCE(NULLIF(btrim(p_fulfillment_type), ''), 'pickup');
    IF v_fulfillment NOT IN ('pickup', 'delivery') THEN
        RAISE EXCEPTION 'Hình thức nhận hàng không hợp lệ: %', p_fulfillment_type
            USING ERRCODE = 'check_violation';
    END IF;

    v_address := NULLIF(btrim(COALESCE(p_delivery_address, '')), '');
    IF v_fulfillment = 'delivery' THEN
        IF v_address IS NULL OR char_length(v_address) < 10 THEN
            RAISE EXCEPTION 'Đơn giao hàng cần địa chỉ nhận cụ thể (ít nhất 10 ký tự).'
                USING ERRCODE = 'check_violation';
        END IF;
        IF char_length(v_address) > 300 THEN
            RAISE EXCEPTION 'Địa chỉ giao hàng không được quá 300 ký tự.'
                USING ERRCODE = 'check_violation';
        END IF;
    ELSE
        v_address := NULL;
    END IF;

    IF p_customer_message IS NOT NULL THEN
        p_customer_message := NULLIF(btrim(p_customer_message), '');
        IF p_customer_message IS NOT NULL AND char_length(p_customer_message) > 200 THEN
            RAISE EXCEPTION 'Nội dung ghi trên bánh không được quá 200 ký tự.'
                USING ERRCODE = 'check_violation';
        END IF;
    END IF;

    IF p_idempotency_key IS NOT NULL THEN
        INSERT INTO public.order_idempotency (customer_id, idempotency_key)
        VALUES (p_customer_id, p_idempotency_key)
        ON CONFLICT (customer_id, idempotency_key) DO NOTHING
        RETURNING TRUE INTO v_claimed;

        IF v_claimed IS DISTINCT FROM TRUE THEN
            SELECT oi.order_id INTO v_order_id
            FROM public.order_idempotency AS oi
            WHERE oi.customer_id = p_customer_id
              AND oi.idempotency_key = p_idempotency_key;

            IF v_order_id IS NOT NULL THEN
                SELECT o.total_price, o.voucher_discount, o.status, o.voucher_code
                INTO v_total, v_discount, v_status, v_voucher_code
                FROM public.orders AS o
                WHERE o.id = v_order_id;
                v_discount := COALESCE(v_discount, 0);
                v_subtotal := v_total + v_discount;
                RETURN QUERY SELECT v_order_id, v_subtotal, v_discount,
                    v_total, TRUE, v_status, v_voucher_code;
                RETURN;
            END IF;

            RAISE EXCEPTION 'Đơn hàng trùng đang được tạo, vui lòng thử lại.'
                USING ERRCODE = 'serialization_failure';
        END IF;
    END IF;

    -- Phải gắn alias `v` vì RETURNS TABLE đã tạo biến OUT tên `status` và `voucher_code`.
    IF p_voucher_code IS NOT NULL AND btrim(p_voucher_code) <> '' THEN
        UPDATE public.vouchers AS v
        SET status = 'used',
            used_at = now()
        WHERE v.code = upper(btrim(p_voucher_code))
          AND v.status = 'active'
          AND v.used_at IS NULL
          AND (v.expires_at IS NULL OR v.expires_at > now())
          AND v.user_id = p_customer_id
        RETURNING v.id INTO v_voucher_id;

        IF v_voucher_id IS NULL THEN
            RAISE EXCEPTION 'Voucher không còn hiệu lực hoặc đã được dùng.'
                USING ERRCODE = 'check_violation';
        END IF;
    END IF;

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
        PERFORM 1 FROM public.branches AS b
        WHERE b.id = p_branch_id AND b.is_active = TRUE;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'Chi nhánh nhận bánh không tồn tại hoặc không hoạt động.'
                USING ERRCODE = 'foreign_key_violation';
        END IF;

        FOR v_item IN SELECT * FROM jsonb_array_elements(COALESCE(p_items, '[]'::jsonb))
        LOOP
            v_product_id := NULLIF(v_item->>'product_id', '')::uuid;
            IF v_product_id IS NULL THEN
                CONTINUE;
            END IF;

            v_remaining := (v_item->>'quantity')::integer;
            FOR v_batch IN
                SELECT pb.id, pb.quantity, pb.quantity_sold
                FROM public.product_batches AS pb
                WHERE pb.product_id = v_product_id
                  AND pb.branch_id = p_branch_id
                  AND pb.is_active = TRUE
                  AND pb.expires_at >= CURRENT_DATE
                  AND pb.quantity_sold < pb.quantity
                ORDER BY pb.expires_at ASC, pb.produced_at ASC, pb.id ASC
                FOR UPDATE
            LOOP
                EXIT WHEN v_remaining <= 0;
                v_take := LEAST(v_remaining, v_batch.quantity - v_batch.quantity_sold);
                UPDATE public.product_batches AS pb
                SET quantity_sold = pb.quantity_sold + v_take,
                    updated_at = now()
                WHERE pb.id = v_batch.id;
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
        voucher_code, voucher_discount, customer_message,
        fulfillment_type, delivery_address
    )
    VALUES (
        p_customer_id, p_branch_id, 'pending', p_total_price, p_pickup_date,
        p_full_name, p_phone, p_email, p_ai_summary,
        p_voucher_code, COALESCE(p_voucher_discount, 0), p_customer_message,
        v_fulfillment, v_address
    )
    RETURNING public.orders.id INTO v_order_id;

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
        RETURNING public.order_items.id INTO v_item_id;

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
        UPDATE public.order_idempotency AS oi
        SET order_id = v_order_id
        WHERE oi.customer_id = p_customer_id
          AND oi.idempotency_key = p_idempotency_key;
    END IF;

    v_subtotal := p_total_price + COALESCE(p_voucher_discount, 0);
    v_discount := COALESCE(p_voucher_discount, 0);
    v_total := p_total_price;

    RETURN QUERY SELECT v_order_id, v_subtotal, v_discount, v_total,
        v_duplicate, 'pending'::TEXT, p_voucher_code;
END;
$$;

REVOKE EXECUTE ON FUNCTION public.rpc_create_order(UUID, TEXT, TEXT, TEXT, TIMESTAMPTZ, INTEGER, TEXT, TEXT, INTEGER, JSONB, JSONB, TEXT, UUID, TEXT, TEXT, TEXT) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.rpc_create_order(UUID, TEXT, TEXT, TEXT, TIMESTAMPTZ, INTEGER, TEXT, TEXT, INTEGER, JSONB, JSONB, TEXT, UUID, TEXT, TEXT, TEXT) FROM anon;
REVOKE EXECUTE ON FUNCTION public.rpc_create_order(UUID, TEXT, TEXT, TEXT, TIMESTAMPTZ, INTEGER, TEXT, TEXT, INTEGER, JSONB, JSONB, TEXT, UUID, TEXT, TEXT, TEXT) FROM authenticated;
GRANT EXECUTE ON FUNCTION public.rpc_create_order(UUID, TEXT, TEXT, TEXT, TIMESTAMPTZ, INTEGER, TEXT, TEXT, INTEGER, JSONB, JSONB, TEXT, UUID, TEXT, TEXT, TEXT) TO service_role;

-- ─── 2. Fix purchases_voucher_discount_check for large / 100% vouchers ─────

ALTER TABLE public.purchases
    DROP CONSTRAINT IF EXISTS purchases_voucher_discount_check;

ALTER TABLE public.purchases
    ADD CONSTRAINT purchases_voucher_discount_check
    CHECK (voucher_discount >= 0 AND total_price >= 0);

-- ─── 3. RPC: rpc_merge_vouchers (gộp nhiều voucher active thành 1 mã lớn) ──

CREATE OR REPLACE FUNCTION public.rpc_merge_vouchers(
    p_user_id UUID,
    p_voucher_ids UUID[] DEFAULT NULL,
    p_new_code TEXT DEFAULT NULL
)
RETURNS TABLE(
    voucher_id UUID,
    code TEXT,
    discount_vnd INTEGER,
    merged_count INTEGER,
    expires_at TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_requested_ids UUID[];
    v_selected_ids UUID[] := ARRAY[]::UUID[];
    v_total_discount INTEGER := 0;
    v_min_expires TIMESTAMPTZ := NULL;
    v_merged_count INTEGER := 0;
    v_new_id UUID;
    v_clean_code TEXT;
    v_rec RECORD;
BEGIN
    v_clean_code := upper(btrim(COALESCE(p_new_code, '')));
    IF v_clean_code = '' THEN
        RAISE EXCEPTION 'INVALID_VOUCHER_CODE' USING ERRCODE = 'P0001';
    END IF;

    IF p_voucher_ids IS NOT NULL THEN
        SELECT ARRAY(SELECT DISTINCT x FROM unnest(p_voucher_ids) AS x)
        INTO v_requested_ids;
    END IF;

    FOR v_rec IN
        SELECT v.id, v.discount_vnd, v.expires_at
        FROM public.vouchers AS v
        WHERE v.user_id = p_user_id
          AND v.status = 'active'
          AND v.used_at IS NULL
          AND (v.expires_at IS NULL OR v.expires_at > now())
          AND (v_requested_ids IS NULL OR v.id = ANY(v_requested_ids))
        ORDER BY v.id ASC
        FOR UPDATE
    LOOP
        v_selected_ids := array_append(v_selected_ids, v_rec.id);
        v_total_discount := v_total_discount + COALESCE(v_rec.discount_vnd, 0);
        v_merged_count := v_merged_count + 1;
        IF v_rec.expires_at IS NOT NULL THEN
            IF v_min_expires IS NULL OR v_rec.expires_at < v_min_expires THEN
                v_min_expires := v_rec.expires_at;
            END IF;
        END IF;
    END LOOP;

    IF v_requested_ids IS NOT NULL AND v_merged_count <> COALESCE(array_length(v_requested_ids, 1), 0) THEN
        RAISE EXCEPTION 'SOME_VOUCHERS_UNAVAILABLE' USING ERRCODE = 'P0001';
    END IF;

    IF v_merged_count < 2 OR v_total_discount <= 0 THEN
        RAISE EXCEPTION 'NEED_AT_LEAST_TWO_VOUCHERS' USING ERRCODE = 'P0001';
    END IF;

    UPDATE public.vouchers AS v
    SET status = 'used',
        used_at = now()
    WHERE v.id = ANY(v_selected_ids)
      AND v.status = 'active';

    INSERT INTO public.vouchers (code, user_id, discount_vnd, status, expires_at)
    VALUES (v_clean_code, p_user_id, v_total_discount, 'active', v_min_expires)
    RETURNING public.vouchers.id INTO v_new_id;

    RETURN QUERY SELECT v_new_id, v_clean_code, v_total_discount, v_merged_count, v_min_expires;
END;
$$;

REVOKE EXECUTE ON FUNCTION public.rpc_merge_vouchers(UUID, UUID[], TEXT) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.rpc_merge_vouchers(UUID, UUID[], TEXT) FROM anon;
REVOKE EXECUTE ON FUNCTION public.rpc_merge_vouchers(UUID, UUID[], TEXT) FROM authenticated;
GRANT EXECUTE ON FUNCTION public.rpc_merge_vouchers(UUID, UUID[], TEXT) TO service_role;

NOTIFY pgrst, 'reload schema';
