-- Migration: make reviews.order_id nullable
-- Reason: Allow reviews without requiring a linked order
-- (product reviews can be submitted directly without order verification)

ALTER TABLE reviews ALTER COLUMN order_id DROP NOT NULL;
