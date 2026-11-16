-- Hai thứ khách cần để "chốt đơn" mà bảng `orders` chưa có chỗ lưu:
--   * khách GIAO HÀNG tận nơi hay GHÉ LẤY tại quán;
--   * nếu giao hàng thì giao tới địa chỉ nào.
--
-- Trước migration này `pickup_date` là mốc duy nhất, nên đơn giao hàng và đơn
-- ghé lấy không phân biệt được: thợ làm xong không biết phải giao hay chờ khách.
-- Nhét địa chỉ vào `ai_summary` (vốn là tóm tắt cho thợ) sẽ làm hỏng cả hai
-- nghĩa, và không kiểm tra được độ dài.
--
-- Voucher cho bánh ngọt: bảng `purchases` (luồng mua bánh ngọt trả tiền ngay)
-- trước đây không có cột voucher, nên mã khách đổi bằng điểm bị bỏ qua im lặng.
-- Trang thanh toán vẫn hiện ô nhập mã cho cả hai luồng, nên khách nhập xong
-- không thấy giảm giá và tưởng voucher hỏng.

-- ─── 1. Hình thức nhận hàng ──────────────────────────────────────────────────

ALTER TABLE public.orders
    ADD COLUMN IF NOT EXISTS fulfillment_type TEXT NOT NULL DEFAULT 'pickup';

ALTER TABLE public.orders
    DROP CONSTRAINT IF EXISTS orders_fulfillment_type_check;

ALTER TABLE public.orders
    ADD CONSTRAINT orders_fulfillment_type_check
    CHECK (fulfillment_type IN ('pickup', 'delivery'));

ALTER TABLE public.orders
    ADD COLUMN IF NOT EXISTS delivery_address TEXT;

ALTER TABLE public.orders
    DROP CONSTRAINT IF EXISTS orders_delivery_address_check;

-- Giao hàng mà không có địa chỉ là đơn không thực hiện được. Chặn ở tầng CSDL
-- để không có đường nào (API, trợ lý AI, SQL tay) tạo ra đơn giao hàng thiếu địa
-- chỉ. Đơn ghé lấy thì địa chỉ phải rỗng.
ALTER TABLE public.orders
    ADD CONSTRAINT orders_delivery_address_check
    CHECK (
        (fulfillment_type = 'delivery'
            AND delivery_address IS NOT NULL
            AND char_length(btrim(delivery_address)) BETWEEN 10 AND 300)
        OR
        (fulfillment_type = 'pickup' AND delivery_address IS NULL)
    );

-- ─── 2. Voucher cho lượt mua bánh ngọt ───────────────────────────────────────

ALTER TABLE public.purchases
    ADD COLUMN IF NOT EXISTS voucher_code TEXT;

ALTER TABLE public.purchases
    ADD COLUMN IF NOT EXISTS voucher_discount INTEGER NOT NULL DEFAULT 0;

ALTER TABLE public.purchases
    DROP CONSTRAINT IF EXISTS purchases_voucher_discount_check;

ALTER TABLE public.purchases
    ADD CONSTRAINT purchases_voucher_discount_check
    CHECK (voucher_discount >= 0 AND voucher_discount <= total_price);

-- ─── 3. rpc_create_order: thêm hình thức nhận + địa chỉ ──────────────────────
-- Giữ nguyên cách làm cũ: DROP chữ ký cũ trước khi tạo chữ ký mới, vì
-- PostgREST phân giải hàm theo số tham số và hai bản cùng tên sẽ mơ hồ.

DROP FUNCTION IF EXISTS public.rpc_create_order(
    UUID, TEXT, TEXT, TEXT, TIMESTAMPTZ, INTEGER, TEXT, TEXT, INTEGER,
    JSONB, JSONB, TEXT, UUID, TEXT
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
    -- ── Hình thức nhận hàng ──────────────────────────────────────────────
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
        -- Ghé lấy tại quán thì địa chỉ giao hàng là vô nghĩa; bỏ đi để không
        -- lưu hai nguồn sự thật mâu thuẫn nhau.
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
        voucher_code, voucher_discount, customer_message,
        fulfillment_type, delivery_address
    )
    VALUES (
        p_customer_id, p_branch_id, 'pending', p_total_price, p_pickup_date,
        p_full_name, p_phone, p_email, p_ai_summary,
        p_voucher_code, COALESCE(p_voucher_discount, 0), p_customer_message,
        v_fulfillment, v_address
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

REVOKE EXECUTE ON FUNCTION public.rpc_create_order(UUID, TEXT, TEXT, TEXT, TIMESTAMPTZ, INTEGER, TEXT, TEXT, INTEGER, JSONB, JSONB, TEXT, UUID, TEXT, TEXT, TEXT) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.rpc_create_order(UUID, TEXT, TEXT, TEXT, TIMESTAMPTZ, INTEGER, TEXT, TEXT, INTEGER, JSONB, JSONB, TEXT, UUID, TEXT, TEXT, TEXT) FROM anon;
REVOKE EXECUTE ON FUNCTION public.rpc_create_order(UUID, TEXT, TEXT, TEXT, TIMESTAMPTZ, INTEGER, TEXT, TEXT, INTEGER, JSONB, JSONB, TEXT, UUID, TEXT, TEXT, TEXT) FROM authenticated;
GRANT EXECUTE ON FUNCTION public.rpc_create_order(UUID, TEXT, TEXT, TEXT, TIMESTAMPTZ, INTEGER, TEXT, TEXT, INTEGER, JSONB, JSONB, TEXT, UUID, TEXT, TEXT, TEXT) TO service_role;

NOTIFY pgrst, 'reload schema';
