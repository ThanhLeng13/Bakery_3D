-- Record which voucher an order used, so the discount is auditable.
--
-- Vouchers already existed (redeemed from loyalty points) but nothing recorded
-- their use on an order: `create_order` had no voucher field at all, so a
-- customer could redeem points and never spend the voucher.
--
-- These two columns store the code and the discount actually applied. The
-- discount is a copy of `vouchers.discount_vnd` at the time of the order, on
-- purpose: if the voucher row later changes, the historical order total must
-- not change with it.
--
-- `total_price` keeps holding the amount actually charged (after discount), so
-- existing readers need no change.

ALTER TABLE public.orders
    ADD COLUMN IF NOT EXISTS voucher_code TEXT,
    ADD COLUMN IF NOT EXISTS voucher_discount INTEGER NOT NULL DEFAULT 0;

COMMENT ON COLUMN public.orders.voucher_code IS
    'Mã voucher đã dùng cho đơn này (NULL nếu không dùng).';
COMMENT ON COLUMN public.orders.voucher_discount IS
    'Số tiền giảm VND đã áp dụng; total_price đã trừ khoản này.';

-- Backfill nothing: historical orders were created without a voucher, and the
-- default of 0 matches that. Rows are only written from here on.

NOTIFY pgrst, 'reload schema';