-- SỬA LỖI HÀM match_cakes (lần 2)
--
-- Lỗi 1: "Returned type integer does not match expected type numeric in column 6"
--        → base_price khai NUMERIC nhưng products.base_price là INTEGER.
-- Lỗi 2: "cannot change return type of existing function"
--        → CREATE OR REPLACE không đổi được kiểu trả về. Phải DROP trước.
--
-- File này DROP rồi CREATE lại hàm. An toàn:
--   - Chỉ đụng tới HÀM, không đụng bảng cake_embeddings hay dữ liệu
--   - DROP ... IF EXISTS nên chạy lại nhiều lần không lỗi
--
-- Chạy file này trong Supabase SQL Editor.

-- Bắt buộc: phải DROP trước vì kiểu trả về thay đổi (NUMERIC → INTEGER).
-- Chữ ký phải khớp CHÍNH XÁC với hàm đang tồn tại:
--   match_cakes(public.vector, double precision, integer)
-- FLOAT trong Postgres = double precision; INT = integer.
--
-- Dùng "public.vector" thay vì "vector" trần: kiểu vector thuộc extension
-- pgvector, nếu search_path của session không chứa schema chứa extension thì
-- "vector" trần sẽ không resolve được và lệnh DROP báo "type does not exist",
-- khiến hàm cũ không bị xóa và lỗi vẫn còn nguyên.
DROP FUNCTION IF EXISTS public.match_cakes(public.vector, double precision, integer);

CREATE FUNCTION public.match_cakes(
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

-- Xác nhận hàm đã được tạo lại với kiểu đúng.
DO $$
DECLARE
    ret_type TEXT;
BEGIN
    SELECT pg_get_function_result(oid) INTO ret_type
    FROM pg_proc
    WHERE proname = 'match_cakes'
      AND pronamespace = 'public'::regnamespace;

    IF ret_type IS NULL THEN
        RAISE EXCEPTION 'match_cakes khong ton tai sau khi tao';
    END IF;

    IF ret_type NOT LIKE '%base_price integer%' THEN
        RAISE EXCEPTION 'Kieu base_price van sai. Ket qua: %', ret_type;
    END IF;

    RAISE NOTICE 'THANH CONG: match_cakes da tao lai voi base_price INTEGER';
END $$;
