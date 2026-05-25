-- Migration: create_product_review_stats_view
-- Description: Create a view that pre-aggregates review count and average rating per product.
-- This eliminates the need to fetch all review rows in the application layer.

CREATE OR REPLACE VIEW product_review_stats AS
SELECT
    product_id,
    COUNT(*)::int        AS review_count,
    ROUND(AVG(rating), 1) AS average_rating
FROM reviews
GROUP BY product_id;
