-- Migration: Bảng vouchers — lưu trữ tất cả mã voucher được phát hành
-- Created: 2026-06-12
--
-- Mỗi voucher được tạo ra khi khách hàng đổi điểm tích lũy.
-- Giúp nhân viên xác minh mã hợp lệ, tránh gian lận và mất mã.

-- ─── 1. Bảng vouchers ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS vouchers (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    code            TEXT        NOT NULL UNIQUE,            -- mã voucher (BNB-XXXXXXXXXXXXXXXX)
    user_id         UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    discount_vnd    INTEGER     NOT NULL,                   -- giá trị giảm (VND)
    status          TEXT        NOT NULL DEFAULT 'active'   -- trạng thái
                        CHECK (status IN ('active', 'used', 'expired')),
    transaction_id  UUID        REFERENCES loyalty_transactions(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    used_at         TIMESTAMPTZ,                            -- thời điểm đã dùng (NULL nếu chưa)
    expires_at      TIMESTAMPTZ                             -- hạn dùng (NULL = không hết hạn)
);

-- ─── 2. Indexes ───────────────────────────────────────────────────────────────
-- Lookup theo code (nhân viên quét mã)
CREATE INDEX IF NOT EXISTS idx_vouchers_code
    ON vouchers(code);

-- Lookup theo user (xem danh sách voucher của khách)
CREATE INDEX IF NOT EXISTS idx_vouchers_user_id
    ON vouchers(user_id, created_at DESC);

-- ─── 3. Row Level Security ────────────────────────────────────────────────────
ALTER TABLE vouchers ENABLE ROW LEVEL SECURITY;

-- Khách hàng chỉ xem voucher của chính mình
CREATE POLICY "Customer can view own vouchers"
    ON vouchers FOR SELECT
    USING (auth.uid() = user_id);

-- service_role bypass RLS (có thể INSERT/UPDATE)
-- (service_role key vốn bypass RLS)
