-- MỞ RỘNG KHO BÁNH SINH NHẬT (15 kiểu mẫu)
--
-- BỐI CẢNH
--   Hiện kho có 4 bánh kem nhưng TẤT CẢ đều `is_active = FALSE`, nên hàm
--   `match_cakes` lọc sạch chúng (`WHERE p.is_active IS TRUE`). Kiểm tra thực tế:
--   gọi match_cakes trả về 18 sản phẩm, TẤT CẢ đều là `sweet`, không có `cake`
--   nào. Nghĩa là chức năng tìm bánh sinh nhật bằng ảnh HIỆN KHÔNG THỂ chạy,
--   bất kể model hay độ chính xác.
--
--   Migration này tạo 15 kiểu mẫu bánh sinh nhật đang bán, để có chỗ gắn ảnh.
--
-- VIỆC CÒN LẠI SAU KHI CHẠY
--   Bảng này chỉ tạo SẢN PHẨM. Chưa có ảnh thì CLIP vẫn không match được.
--   Cần: tải ảnh lên Supabase Storage (bucket `product-images`), thêm dòng vào
--   `product_images`, rồi chạy `python scripts/embed_catalog.py`.
--   Xem backend/scripts/import_cake_images.py để làm tự động.
--
-- CHẠY FILE NÀY TRONG SUPABASE SQL EDITOR.
-- An toàn: dùng ON CONFLICT theo `name` nên chạy lại nhiều lần không tạo trùng.

-- ─── 1. Bảo đảm có ràng buộc duy nhất trên name để ON CONFLICT hoạt động ──────
-- Nếu đã có unique index/constraint thì bỏ qua.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'products_name_key'
           AND conrelid = 'public.products'::regclass
    ) AND NOT EXISTS (
        SELECT 1 FROM pg_indexes
         WHERE indexname = 'products_name_key'
           AND tablename = 'products'
    ) THEN
        -- Không tự thêm nếu đang có dữ liệu trùng tên, vì sẽ lỗi.
        IF (SELECT count(*) FROM (
                SELECT name FROM public.products GROUP BY name HAVING count(*) > 1
            ) d) = 0 THEN
            ALTER TABLE public.products ADD CONSTRAINT products_name_key UNIQUE (name);
            RAISE NOTICE 'Da them rang buoc unique tren products.name';
        ELSE
            RAISE WARNING 'Co san pham trung ten, BO QUA buoc them unique. '
                          'Hay xu ly trung ten roi chay lai.';
        END IF;
    ELSE
        RAISE NOTICE 'Da co rang buoc unique tren products.name';
    END IF;
END $$;

-- ─── 2. Thêm 15 kiểu mẫu bánh sinh nhật ──────────────────────────────────────
--
-- Chọn theo kiểu mẫu phổ biến của tiệm bánh sinh nhật Việt Nam, chia nhóm để
-- khách tìm theo dịp:
--   - Theo dịp   : bé trai, bé gái, người lớn, kỷ niệm
--   - Theo trang trí: hoa tươi, hoa buttercream, trái cây, socola, minimal
--   - Theo cấu trúc : 1 tầng, 2 tầng, 3 tầng
--
-- `base_price` là giá khởi điểm (bánh 16cm), vì giá bánh sinh nhật thay đổi
-- theo kích thước và yêu cầu trang trí.
INSERT INTO public.products (name, description, base_price, category, product_type, is_active)
VALUES
    ('Bánh sinh nhật bé trai siêu nhân',
     'Bánh kem 1 tầng trang trí hình siêu nhân, phù hợp tiệc sinh nhật bé trai. Nhận đặt theo màu yêu thích.',
     320000, 'bánh âu', 'cake', TRUE),

    ('Bánh sinh nhật bé gái công chúa',
     'Bánh kem 1 tầng trang trí vương miện và hoa, tông hồng pastel, phù hợp tiệc sinh nhật bé gái.',
     320000, 'bánh âu', 'cake', TRUE),

    ('Bánh sinh nhật hoa tươi',
     'Bánh kem phủ hoa tươi theo mùa, kem tươi nhẹ. Hoa tươi đặt riêng trong ngày nên cần đặt trước 24 giờ.',
     420000, 'bánh âu', 'cake', TRUE),

    ('Bánh sinh nhật hoa buttercream',
     'Bánh kem trang trí hoa buttercream thủ công, giữ form đẹp lâu, phù hợp chụp ảnh và di chuyển xa.',
     380000, 'bánh âu', 'cake', TRUE),

    ('Bánh sinh nhật 2 tầng hoa hồng',
     'Bánh kem 2 tầng sang trọng, trang trí hoa hồng buttercream, phù hợp tiệc lớn và kỷ niệm.',
     750000, 'bánh âu', 'cake', TRUE),

    ('Bánh sinh nhật 2 tầng tối giản',
     'Bánh kem 2 tầng thiết kế tối giản, kem mịn một màu, điểm nhấn chữ viết tay. Phong cách Hàn Quốc.',
     680000, 'bánh âu', 'cake', TRUE),

    ('Bánh sinh nhật trái cây tươi',
     'Bánh kem phủ trái cây tươi theo mùa: dâu, kiwi, việt quất, xoài. Vị thanh, ít ngọt.',
     400000, 'bánh âu', 'cake', TRUE),

    ('Bánh sinh nhật socola',
     'Bánh kem socola với ganache mượt, trang trí socola thanh và cầu socola. Vị đậm, phù hợp người lớn.',
     380000, 'bánh âu', 'cake', TRUE),

    ('Bánh sinh nhật matcha',
     'Bánh kem trà xanh Nhật Bản, whipped cream nhẹ, trang trí bột matcha. Vị thanh, hơi đắng nhẹ.',
     400000, 'bánh âu', 'cake', TRUE),

    ('Bánh sinh nhật red velvet',
     'Bánh kem red velvet màu đỏ đặc trưng, phủ cream cheese, trang trí vụn bánh. Phù hợp kỷ niệm.',
     420000, 'bánh âu', 'cake', TRUE),

    ('Bánh sinh nhật minimal Hàn Quốc',
     'Bánh kem tối giản kiểu Hàn: kem mịn một khối, chữ viết tay, hoa khô điểm nhẹ. Phong cách sang trọng.',
     360000, 'bánh âu', 'cake', TRUE),

    ('Bánh sinh nhật con vật đáng yêu',
     'Bánh kem tạo hình con vật (gấu, thỏ, mèo) bằng fondant, phù hợp tiệc thiếu nhi.',
     350000, 'bánh âu', 'cake', TRUE),

    ('Bánh sinh nhật số tuổi',
     'Bánh kem tạo hình số tuổi, trang trí theo màu chủ đề khách chọn. Nhận mọi số từ 0 đến 99.',
     340000, 'bánh âu', 'cake', TRUE),

    ('Bánh sinh nhật người lớn thanh lịch',
     'Bánh kem trang trí thanh lịch cho người lớn: tông trắng kem, điểm vàng gold, hoa khô. Ít ngọt.',
     450000, 'bánh âu', 'cake', TRUE),

    ('Bánh sinh nhật 3 tầng cưới hỏi',
     'Bánh kem 3 tầng dùng cho tiệc cưới, kỷ niệm hoặc sự kiện lớn. Thiết kế theo yêu cầu, cần đặt trước 72 giờ.',
     1450000, 'bánh âu', 'cake', TRUE)
ON CONFLICT (name) DO UPDATE
    SET description  = EXCLUDED.description,
        base_price   = EXCLUDED.base_price,
        category     = EXCLUDED.category,
        product_type = EXCLUDED.product_type,
        is_active    = EXCLUDED.is_active;

-- ─── 3. Bật 4 bánh kem cũ đang bị ẩn ─────────────────────────────────────────
-- Bốn sản phẩm này đã có trong kho nhưng is_active = FALSE nên không bao giờ
-- xuất hiện trong kết quả tìm kiếm. Bật lên để chúng dùng được.
UPDATE public.products
   SET is_active = TRUE
 WHERE product_type = 'cake'
   AND is_active IS NOT TRUE;

-- ─── 4. Xác nhận ─────────────────────────────────────────────────────────────
DO $$
DECLARE
    n_total  INT;
    n_active INT;
BEGIN
    SELECT count(*) INTO n_total FROM public.products WHERE product_type = 'cake';
    SELECT count(*) INTO n_active FROM public.products
     WHERE product_type = 'cake' AND is_active IS TRUE;

    RAISE NOTICE 'Banh kem: % tong, % dang ban', n_total, n_active;

    IF n_active < 15 THEN
        RAISE WARNING 'Chi co % banh kem dang ban. Kiem tra lai phan INSERT.', n_active;
    END IF;
END $$;

-- ─── 5. KIỂM TRA SAU KHI CHẠY ─────────────────────────────────────────────────
-- Chạy truy vấn này để xem danh sách. Cột `co_anh` = 0 nghĩa là CLIP CHƯA
-- match được, cần thêm ảnh.
--
--   SELECT p.name,
--          p.base_price,
--          count(pi.id) AS so_anh,
--          count(ce.id) AS so_embedding
--     FROM public.products p
--     LEFT JOIN public.product_images pi ON pi.product_id = p.id
--     LEFT JOIN public.cake_embeddings ce ON ce.product_id = p.id
--    WHERE p.product_type = 'cake' AND p.is_active IS TRUE
--    GROUP BY p.id, p.name, p.base_price
--    ORDER BY so_embedding, p.name;
--
-- Kết quả mong đợi hiện tại: tất cả đều 0 ảnh. Đó là việc tiếp theo cần làm.
