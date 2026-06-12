-- Migration: Ràng buộc duy nhất cho loyalty_transactions và cập nhật RPC
-- Created: 2026-06-12
--
-- Ngăn ngừa double-crediting khi award_points bị gọi nhiều lần với cùng một order/purchase.

-- 1. Thêm UNIQUE constraint vào loyalty_transactions
ALTER TABLE loyalty_transactions 
    ADD CONSTRAINT unique_user_type_ref UNIQUE (user_id, type, ref_id);
