-- GỘP EMBEDDING TRÙNG THEO SẢN PHẨM TRONG match_cakes
--
-- VẤN ĐỀ
--   `cake_embeddings` có thể chứa nhiều dòng cho cùng một sản phẩm, vì
--   `embed_catalog.py` sinh embedding cho TỪNG ẢNH và upsert theo
--   (product_id, image_url). Kiểm tra trên dữ liệu thật: 20 embedding trải
--   trên 18 sản phẩm, tức 2 sản phẩm có 2 ảnh.
--
--   Hàm cũ JOIN thẳng nên một sản phẩm khớp ở cả 2 ảnh sẽ chiếm 2 suất trong
--   top-K. Khách xin 6 kết quả nhưng thực chất chỉ nhận được 5 sản phẩm khác
--   nhau — ít lựa chọn hơn họ tưởng.
--
-- CÁCH SỬA
--   DISTINCT ON (product_id) giữ đúng ảnh gần nhất (khoảng cách nhỏ nhất) cho
--   mỗi sản phẩm, rồi mới lọc ngưỡng, sắp xếp và cắt LIMIT.
--
--   Lưu ý thứ tự: DISTINCT ON phải chạy TRƯỚC khi cắt LIMIT, nếu không thì
--   việc gộp trùng sẽ không đủ chỗ để bù vào số suất đã mất.
--
-- ĐÁNH ĐỔI ĐÃ BIẾT
--   DISTINCT ON buộc Postgres sắp xếp toàn bộ bảng embedding, nên HNSW index
--   không được dùng cho bước gộp. Với 20 embedding thì không đáng kể (đo được
--   ~84ms, ngang một truy vấn 1 dòng). Khi kho lên hàng chục nghìn embedding
--   thì cần chuyển sang LATERAL join có giới hạn ứng viên, hoặc chỉ đánh index
--   một ảnh đại diện cho mỗi sản phẩm.
--
-- CHẠY FILE NÀY TRONG SUPABASE SQL EDITOR.
-- An toàn: chỉ DROP và CREATE lại HÀM, không đụng bảng hay dữ liệu.
-- Chạy lại nhiều lần không lỗi.

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
    FROM (
        -- Một dòng cho mỗi sản phẩm: ảnh có khoảng cách nhỏ nhất.
        -- ORDER BY phải bắt đầu bằng đúng cột trong DISTINCT ON.
        SELECT DISTINCT ON (ce.product_id)
               ce.product_id, ce.image_url, ce.embedding
        FROM public.cake_embeddings ce
        ORDER BY ce.product_id, ce.embedding <=> query_embedding
    ) ce
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

-- Xác nhận: hàm tồn tại, đúng kiểu trả về, và KHÔNG còn nhánh JOIN trực tiếp.
DO $$
DECLARE
    ret_type   TEXT;
    fn_source  TEXT;
BEGIN
    SELECT pg_get_function_result(oid), prosrc
      INTO ret_type, fn_source
      FROM pg_proc
     WHERE proname = 'match_cakes'
       AND pronamespace = 'public'::regnamespace;

    IF ret_type IS NULL THEN
        RAISE EXCEPTION 'match_cakes khong ton tai sau khi tao';
    END IF;

    IF ret_type NOT LIKE '%base_price integer%' THEN
        RAISE EXCEPTION 'Kieu base_price sai. Ket qua: %', ret_type;
    END IF;

    IF fn_source NOT LIKE '%DISTINCT ON%' THEN
        RAISE EXCEPTION 'Ham thieu DISTINCT ON - chua gop trung theo san pham';
    END IF;

    RAISE NOTICE 'THANH CONG: match_cakes da gop trung embedding theo product_id';
END $$;

-- KIỂM TRA SAU KHI CHẠY
-- Chạy truy vấn này để xác nhận không còn sản phẩm nào xuất hiện 2 lần.
-- Không thể chạy tự động ở đây vì cần một vector truy vấn cụ thể.
--
--   SELECT product_id, count(*) AS so_lan
--     FROM public.match_cakes(
--            (SELECT embedding FROM public.cake_embeddings LIMIT 1),
--            0.0, 20)
--    GROUP BY product_id
--   HAVING count(*) > 1;
--
-- Kết quả mong đợi: 0 dòng.
