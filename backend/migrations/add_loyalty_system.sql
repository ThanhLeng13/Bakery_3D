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
