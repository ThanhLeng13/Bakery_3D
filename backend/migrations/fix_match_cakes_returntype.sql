-- SỬA LỖI HÀM match_cakes
--
-- Lỗi: "Returned type integer does not match expected type numeric in column 6"
-- Nguyên nhân: khai báo base_price NUMERIC nhưng products.base_price là INTEGER.
-- Cách sửa: đổi sang INTEGER cho khớp.
--
-- Chỉ thay thế hàm, KHÔNG đụng tới bảng hay dữ liệu đã có.
-- File này an toàn để chạy lại nhiều lần.

CREATE OR REPLACE FUNCTION public.match_cakes(
    query_embedding vector(512),
    match_threshold FLOAT DEFAULT 0.0,
    match_count     INT   DEFAULT 5
)
RETURNS TABLE(
    product_id      UUID,
    product_name    TEXT,
    image_url       TEXT,
    category        TEXT,
    product_type    TEXT,
    base_price      INTEGER,
    similarity      FLOAT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id,
        p.name::TEXT,
        ce.image_url,
        p.category::TEXT,
        p.product_type::TEXT,
        p.base_price::INTEGER,
        (1 - (ce.embedding <=> query_embedding))::FLOAT AS similarity
    FROM public.cake_embeddings ce
    JOIN public.products p ON p.id = ce.product_id
    WHERE p.is_active IS TRUE
      AND (1 - (ce.embedding <=> query_embedding)) >= match_threshold
    ORDER BY ce.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

REVOKE EXECUTE ON FUNCTION public.match_cakes(vector, FLOAT, INT) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.match_cakes(vector, FLOAT, INT) FROM anon;
REVOKE EXECUTE ON FUNCTION public.match_cakes(vector, FLOAT, INT) FROM authenticated;
GRANT  EXECUTE ON FUNCTION public.match_cakes(vector, FLOAT, INT) TO   service_role;
