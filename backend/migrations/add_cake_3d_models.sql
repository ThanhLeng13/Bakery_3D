-- KHO MẪU BÁNH 3D — Giai đoạn 1 của đề tài
--
-- Mục tiêu:
--   1. Lưu kho các thân bánh .glb tái sử dụng được.
--   2. Liên kết một hoặc nhiều mẫu 3D với một sản phẩm catalog.
--   3. Không làm mất tính năng tùy chỉnh màu/topping theo vùng: GLB tự sinh
--      giữ các mesh tên Body / Top / Border.
--
-- Nguồn asset hiện tại: frontend/public/models/*.glb
-- URL là đường dẫn public của Next.js, KHÔNG đưa vào Supabase Storage ở giai đoạn này.
-- Chạy file này trong Supabase SQL Editor.
-- An toàn khi chạy lại: mọi câu lệnh đều idempotent.

-- ─── 1. Kho thân bánh 3D ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.cake_3d_models (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug          TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL,
    glb_url       TEXT NOT NULL,
    thumbnail_url TEXT,
    tags          TEXT[] NOT NULL DEFAULT '{}',
    category      TEXT NOT NULL DEFAULT 'birthday',
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT cake_3d_models_slug_format CHECK (slug ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'),
    CONSTRAINT cake_3d_models_glb_url CHECK (glb_url LIKE '%.glb' OR glb_url LIKE '%.glb?%')
);

CREATE INDEX IF NOT EXISTS idx_cake_3d_models_active_category
    ON public.cake_3d_models(category, is_active);
CREATE INDEX IF NOT EXISTS idx_cake_3d_models_tags
    ON public.cake_3d_models USING GIN(tags);

-- ─── 2. Liên kết kho 3D ↔ catalog sản phẩm ───────────────────────────────────
CREATE TABLE IF NOT EXISTS public.product_3d_models (
    product_id UUID NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
    model_id   UUID NOT NULL REFERENCES public.cake_3d_models(id) ON DELETE CASCADE,
    sort_order SMALLINT NOT NULL DEFAULT 0 CHECK (sort_order >= 0),
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (product_id, model_id)
);

CREATE INDEX IF NOT EXISTS idx_product_3d_models_product_sort
    ON public.product_3d_models(product_id, sort_order);
CREATE UNIQUE INDEX IF NOT EXISTS idx_product_3d_models_one_primary
    ON public.product_3d_models(product_id) WHERE is_primary;

-- ─── 3. Seed 6 thân bánh tự sinh ──────────────────────────────────────────────
INSERT INTO public.cake_3d_models (slug, name, glb_url, tags, category, is_active)
VALUES
    ('round-1-tier',  'Bánh tròn 1 tầng',      '/models/cake-tron-1-tang.glb', ARRAY['round', 'one-tier', 'base'], 'birthday', TRUE),
    ('round-2-tier',  'Bánh tròn 2 tầng',      '/models/cake-tron-2-tang.glb', ARRAY['round', 'two-tier', 'base'], 'birthday', TRUE),
    ('round-3-tier',  'Bánh tròn 3 tầng',      '/models/cake-tron-3-tang.glb', ARRAY['round', 'three-tier', 'base', 'wedding'], 'birthday', TRUE),
    ('square-1-tier', 'Bánh vuông 1 tầng',     '/models/cake-vuong-1-tang.glb', ARRAY['square', 'one-tier', 'base'], 'birthday', TRUE),
    ('heart-1-tier',  'Bánh trái tim 1 tầng',  '/models/cake-trai-tim.glb', ARRAY['heart', 'one-tier', 'base', 'romantic'], 'birthday', TRUE),
    ('tall-1-tier',   'Bánh cao 1 tầng',       '/models/cake-cao-1-tang.glb', ARRAY['round', 'tall', 'one-tier', 'base'], 'birthday', TRUE)
ON CONFLICT (slug) DO UPDATE
SET name = EXCLUDED.name,
    glb_url = EXCLUDED.glb_url,
    tags = EXCLUDED.tags,
    category = EXCLUDED.category,
    is_active = EXCLUDED.is_active;

-- ─── 4. Liên kết chính xác với catalog (không suy diễn theo ảnh/tên) ─────────
-- Chỉ liên kết những sản phẩm có silhouette được xác nhận rõ trong tên catalog:
-- hai bánh "trái tim" và bánh "2 tầng". Các bánh ảnh phong cách riêng KHÔNG bị
-- gán đại mẫu tròn; trang chi tiết của chúng tiếp tục hiển thị ảnh cho đến khi
-- nhân viên xác nhận model phù hợp.
INSERT INTO public.product_3d_models (product_id, model_id, sort_order, is_primary)
SELECT p.id, m.id, 0, TRUE
FROM public.products p
JOIN public.cake_3d_models m ON m.slug = CASE
    WHEN lower(p.name) LIKE '%hình trái tim%' OR lower(p.name) LIKE '%trái tim figure%' THEN 'heart-1-tier'
    WHEN lower(p.name) LIKE '%2 tầng%' THEN 'round-2-tier'
END
WHERE p.product_type = 'cake'
  AND p.is_active IS TRUE
  AND (
      lower(p.name) LIKE '%hình trái tim%'
      OR lower(p.name) LIKE '%trái tim figure%'
      OR lower(p.name) LIKE '%2 tầng%'
  )
ON CONFLICT (product_id, model_id) DO UPDATE
SET sort_order = EXCLUDED.sort_order,
    is_primary = EXCLUDED.is_primary;

-- Bảo đảm mỗi sản phẩm chỉ có một mẫu primary nếu migration từng chạy dở.
WITH ranked AS (
    SELECT product_id, model_id,
           row_number() OVER (PARTITION BY product_id ORDER BY is_primary DESC, sort_order, model_id) AS row_no
    FROM public.product_3d_models
)
UPDATE public.product_3d_models links
SET is_primary = (ranked.row_no = 1)
FROM ranked
WHERE links.product_id = ranked.product_id
  AND links.model_id = ranked.model_id;

-- ─── 5. RLS: khách chỉ đọc mẫu đang hoạt động ──────────────────────────────────
ALTER TABLE public.cake_3d_models ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.product_3d_models ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Public can read active cake 3d models" ON public.cake_3d_models;
CREATE POLICY "Public can read active cake 3d models"
    ON public.cake_3d_models FOR SELECT
    USING (is_active IS TRUE);

DROP POLICY IF EXISTS "Public can read active product 3d links" ON public.product_3d_models;
CREATE POLICY "Public can read active product 3d links"
    ON public.product_3d_models FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.cake_3d_models m
            WHERE m.id = model_id AND m.is_active IS TRUE
        )
    );

-- ─── 6. Kiểm tra sau khi chạy ──────────────────────────────────────────────────
DO $$
DECLARE
    model_count INT;
    linked_product_count INT;
BEGIN
    SELECT count(*) INTO model_count FROM public.cake_3d_models WHERE is_active IS TRUE;
    SELECT count(DISTINCT product_id) INTO linked_product_count FROM public.product_3d_models;

    IF model_count <> 6 THEN
        RAISE EXCEPTION 'Kho 3D phai co 6 mau, hien co %', model_count;
    END IF;
    IF linked_product_count = 0 THEN
        RAISE WARNING 'Chua co lien ket catalog duoc xac minh; kho 3D van san sang cho Cake Studio.';
    END IF;

    RAISE NOTICE 'Kho 3D san sang: % mau, lien ket voi % san pham da xac minh', model_count, linked_product_count;
END $$;

-- KIỂM TRA THỦ CÔNG:
-- SELECT m.slug, m.name, m.glb_url, count(l.product_id) AS so_san_pham_lien_ket
-- FROM public.cake_3d_models m
-- LEFT JOIN public.product_3d_models l ON l.model_id = m.id
-- GROUP BY m.id
-- ORDER BY m.slug;
