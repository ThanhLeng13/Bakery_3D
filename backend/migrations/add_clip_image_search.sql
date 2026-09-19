-- Migration: CLIP image search (trụ cột 2 của đề tài)
-- Created: 2026-09-18
--
-- Mục đích: cho phép khách tải lên ảnh bánh yêu thích, hệ thống dùng mô hình
-- thị giác CLIP để tìm mẫu 3D / sản phẩm gần giống nhất trong kho.
--
-- Kiến trúc:
--   1. pgvector lưu vector 512 chiều do CLIP ViT-B-32 sinh ra
--   2. Mỗi ảnh sản phẩm → 1 vector (bảng cake_embeddings)
--   3. Hàm match_cakes: so sánh vector ảnh khách với kho, trả top-K gần nhất
--
-- Idempotent: chạy lại nhiều lần không lỗi.

-- ─── 1. Bật extension pgvector ───────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS vector;

-- ─── 2. Bảng embedding ───────────────────────────────────────────────────────
-- Một dòng = một ảnh đã được vector hóa.
-- product_id là khóa ngoại tới products; image_url để truy vết nguồn.
CREATE TABLE IF NOT EXISTS public.cake_embeddings (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id   UUID NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
    image_url    TEXT NOT NULL,
    -- ViT-B-32 trả vector 512 chiều. Nếu đổi sang model khác (ViT-L-14 = 768)
    -- thì phải đổi số này VÀ sinh lại toàn bộ embedding.
    embedding    vector(512) NOT NULL,
    model_name   TEXT NOT NULL DEFAULT 'ViT-B-32',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Một ảnh chỉ nên có một embedding; cho phép upsert theo cặp này.
    CONSTRAINT cake_embeddings_product_image_key UNIQUE (product_id, image_url)
);

-- ─── 3. Index tìm kiếm vector ────────────────────────────────────────────────
-- HNSW cho phép tìm gần đúng nhanh (approximate nearest neighbour).
-- vector_cosine_ops khớp với toán tử <=> dùng trong match_cakes.
-- Với 20 vector thì index chưa cần thiết, nhưng thêm sẵn để không phải sửa
-- schema khi kho mẫu lớn lên.
CREATE INDEX IF NOT EXISTS idx_cake_embeddings_hnsw
    ON public.cake_embeddings
    USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_cake_embeddings_product_id
    ON public.cake_embeddings(product_id);

-- ─── 4. Row Level Security ───────────────────────────────────────────────────
ALTER TABLE public.cake_embeddings ENABLE ROW LEVEL SECURITY;

-- Embedding không phải dữ liệu riêng tư: khách được đọc để tìm kiếm.
-- Ghi chỉ qua service_role (script sinh embedding), nên không cần policy INSERT.
DROP POLICY IF EXISTS "Anyone can read cake embeddings" ON public.cake_embeddings;
CREATE POLICY "Anyone can read cake embeddings"
    ON public.cake_embeddings FOR SELECT
    USING (true);

-- ─── 5. Hàm tìm kiếm tương đồng ──────────────────────────────────────────────
-- So sánh vector ảnh khách tải lên với toàn bộ kho, trả về top-K.
--
-- Toán tử <=> là cosine distance (0 = giống hệt, 2 = ngược hướng).
-- Độ tương đồng = 1 - distance, dùng để hiển thị phần trăm cho khách.
--
-- Lọc is_active: không gợi ý sản phẩm đã ngừng bán.
-- SECURITY DEFINER + search_path cố định: chống search_path injection.
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
    base_price      NUMERIC,
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
        p.base_price,
        (1 - (ce.embedding <=> query_embedding))::FLOAT AS similarity
    FROM public.cake_embeddings ce
    JOIN public.products p ON p.id = ce.product_id
    WHERE p.is_active IS TRUE
      AND (1 - (ce.embedding <=> query_embedding)) >= match_threshold
    ORDER BY ce.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Chỉ service_role gọi hàm này (backend xử lý ảnh upload rồi mới truy vấn).
REVOKE EXECUTE ON FUNCTION public.match_cakes(vector, FLOAT, INT) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.match_cakes(vector, FLOAT, INT) FROM anon;
REVOKE EXECUTE ON FUNCTION public.match_cakes(vector, FLOAT, INT) FROM authenticated;
GRANT  EXECUTE ON FUNCTION public.match_cakes(vector, FLOAT, INT) TO   service_role;

-- ─── 6. Kiểm tra ─────────────────────────────────────────────────────────────
DO $$
DECLARE
    n_img INT;
    n_vec INT;
BEGIN
    SELECT COUNT(*) INTO n_img FROM public.product_images;
    SELECT COUNT(*) INTO n_vec FROM public.cake_embeddings;
    RAISE NOTICE 'CLIP schema san sang. Anh san pham: %, embedding da sinh: %', n_img, n_vec;
    IF n_vec = 0 THEN
        RAISE NOTICE 'Chay: python backend/scripts/embed_catalog.py  de sinh embedding';
    END IF;
END $$;
