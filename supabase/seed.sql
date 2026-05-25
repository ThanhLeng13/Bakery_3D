-- ============================================================
-- Cake Shop AI Web - Seed Data (Development)
-- ============================================================

-- Insert sample admin user
INSERT INTO users (id, email, full_name, phone, role) VALUES
  ('00000000-0000-0000-0000-000000000001', 'admin@cakeshop.vn', 'Admin Tiệm Bánh', '0901234567', 'admin');

-- Insert sample baker user
INSERT INTO users (id, email, full_name, phone, role) VALUES
  ('00000000-0000-0000-0000-000000000002', 'baker@cakeshop.vn', 'Thợ Bánh Minh', '0912345678', 'baker');

-- Insert sample customer user
INSERT INTO users (id, email, full_name, phone, role) VALUES
  ('00000000-0000-0000-0000-000000000003', 'customer@example.com', 'Nguyễn Văn A', '0923456789', 'customer');

-- Insert sample products
INSERT INTO products (id, name, description, category, base_price, sizes, flavors, is_active) VALUES
  (
    '10000000-0000-0000-0000-000000000001',
    'Bánh Kem Sinh Nhật Dâu Tây',
    'Bánh kem sinh nhật với lớp kem tươi mịn màng, trang trí dâu tây tươi và socola. Phù hợp cho các bữa tiệc sinh nhật ấm cúng.',
    'bánh âu',
    250000,
    '["16cm", "20cm", "24cm", "2-tier"]',
    '["vanilla", "chocolate", "strawberry", "matcha"]',
    true
  ),
  (
    '10000000-0000-0000-0000-000000000002',
    'Bánh Kem Đám Cưới Hoa Hồng',
    'Bánh kem đám cưới sang trọng với hoa hồng buttercream thủ công. Thiết kế tinh tế, phù hợp cho ngày trọng đại.',
    'bánh âu',
    500000,
    '["20cm", "24cm", "2-tier"]',
    '["vanilla", "red velvet", "champagne"]',
    true
  ),
  (
    '10000000-0000-0000-0000-000000000003',
    'Bánh Mousse Trà Xanh',
    'Bánh mousse trà xanh Nhật Bản với lớp mousse mềm mịn, vị trà xanh đậm đà. Ít ngọt, phù hợp người thích vị thanh nhẹ.',
    'bánh ngọt',
    180000,
    '["16cm", "20cm"]',
    '["matcha", "matcha-chocolate"]',
    true
  ),
  (
    '10000000-0000-0000-0000-000000000004',
    'Bánh Kem Socola Đen',
    'Bánh kem socola đen đậm vị với ganache socola Bỉ. Dành cho những tín đồ socola chính hiệu.',
    'bánh âu',
    280000,
    '[{"name": "16cm", "price": 280000}, {"name": "20cm", "price": 380000}, {"name": "24cm", "price": 480000}]'::jsonb,
    '["dark chocolate", "chocolate-orange", "chocolate-mint"]'::jsonb,
    true
  ),
  (
    '10000000-0000-0000-0000-000000000011',
    'Cheesecake Red Velvet',
    'Lớp bánh red velvet mềm mịn xen kẽ kem phô mai béo ngậy trong hũ tiện lợi.',
    'bánh ngọt',
    35000,
    '[{"name": "Hộp", "price": 35000}]'::jsonb,
    '["Red Velvet", "Phô mai"]'::jsonb,
    true
  ),
  (
    '10000000-0000-0000-0000-000000000012',
    'Bánh tiramisu truyền thống',
    'Tiramisu Ý truyền thống thơm hương cà phê espresso và lớp kem mascarpone béo ngậy, phủ cacao và bột trà xanh.',
    'bánh ngọt',
    60000,
    '[{"name": "Hộp", "price": 60000}]'::jsonb,
    '["Cà phê", "Trà xanh"]'::jsonb,
    true
  ),
  (
    '10000000-0000-0000-0000-000000000013',
    'Bánh tiramisu gấu',
    'Tiramisu thơm ngon tạo hình chú gấu dễ thương, phủ bột cacao mịn màng.',
    'bánh ngọt',
    55000,
    '[{"name": "Hộp", "price": 55000}]'::jsonb,
    '["Cà phê", "Socola"]'::jsonb,
    true
  ),
  (
    '10000000-0000-0000-0000-000000000014',
    'Bánh cheese tươi',
    'Bánh kem sữa phô mai tươi mềm mịn, ngọt thanh mát lạnh đựng trong hũ square tiện dụng.',
    'bánh ngọt',
    60000,
    '[{"name": "Hộp", "price": 60000}]'::jsonb,
    '["Phô mai"]'::jsonb,
    true
  ),
  (
    '10000000-0000-0000-0000-000000000015',
    'Bánh phomai sợi dẻo',
    'Bánh phô mai nướng với những sợi phô mai dai dẻo thơm ngậy trên mặt.',
    'bánh ngọt',
    55000,
    '[{"name": "Hộp", "price": 55000}]'::jsonb,
    '["Phô mai"]'::jsonb,
    true
  ),
  (
    '10000000-0000-0000-0000-000000000016',
    'Bánh tart trứng',
    'Bánh tart trứng thơm lừng với vỏ ngàn lớp giòn tan và nhân kem trứng nướng mềm mịn (Hộp 3 cái).',
    'bánh ngọt',
    40000,
    '[{"name": "Hộp 3 cái", "price": 40000}]'::jsonb,
    '["Kem trứng"]'::jsonb,
    true
  ),
  (
    '10000000-0000-0000-0000-000000000017',
    'Bánh kem cốm dẻo',
    'Hương vị cốm dẻo thơm mát truyền thống kết hợp kem whipped cream béo ngọt nhẹ nhàng.',
    'bánh ngọt',
    60000,
    '[{"name": "Hộp", "price": 60000}]'::jsonb,
    '["Cốm dẻo"]'::jsonb,
    true
  ),
  (
    '10000000-0000-0000-0000-000000000018',
    'Bánh khoai lang phô mai',
    'Bánh khoai lang nướng bùi dẻo nhân phô mai kéo sợi thơm ngậy tuyệt hảo (Hộp 2 cái).',
    'bánh ngọt',
    60000,
    '[{"name": "Hộp 2 cái", "price": 60000}]'::jsonb,
    '["Khoai lang", "Phô mai"]'::jsonb,
    true
  ),
  (
    '10000000-0000-0000-0000-000000000019',
    'Bánh mousse chanh dây',
    'Mousse chanh dây chua ngọt tươi mát, lớp thạch vàng óng mượt mà cùng cốt bánh mềm ẩm.',
    'bánh ngọt',
    50000,
    '[{"name": "Hộp", "price": 50000}]'::jsonb,
    '["Chanh dây"]'::jsonb,
    true
  ),
  (
    '10000000-0000-0000-0000-000000000020',
    'Bánh Dark Oreo',
    'Bánh kem oreo cookies & cream giòn bùi thơm lừng vụn bánh oreo đậm đà.',
    'bánh ngọt',
    60000,
    '[{"name": "Hộp", "price": 60000}]'::jsonb,
    '["Oreo", "Cream"]'::jsonb,
    true
  ),
  (
    '10000000-0000-0000-0000-000000000021',
    'Bánh phô mai cháy',
    'Basque Burnt Cheesecake nướng cháy xém bề mặt thơm bùi, nhân phô mai tan chảy béo ngậy tuyệt hảo.',
    'bánh ngọt',
    35000,
    '[{"name": "Cái", "price": 35000}]'::jsonb,
    '["Phô mai"]'::jsonb,
    true
  ),
  (
    '10000000-0000-0000-0000-000000000022',
    'Bánh su kem',
    'Bánh su kem choux pastry mini nhân kem custard sữa ngọt mát mịn màng (Hộp 9 cái).',
    'bánh ngọt',
    50000,
    '[{"name": "Hộp 9 cái", "price": 50000}]'::jsonb,
    '["Vanilla custard"]'::jsonb,
    true
  ),
  (
    '10000000-0000-0000-0000-000000000023',
    'Bánh chuối nướng nước dừa',
    'Bánh chuối nướng dẻo ngọt, thơm đậm đà kết hợp nước cốt dừa béo ngậy.',
    'bánh ngọt',
    45000,
    '[{"name": "Hộp", "price": 45000}]'::jsonb,
    '["Chuối nướng", "Cốt dừa"]'::jsonb,
    true
  ),
  (
    '10000000-0000-0000-0000-000000000024',
    'Bánh Brownie',
    'Brownie chocolate fudge đậm vị đắng ngọt, rắc hạnh nhân lát giòn bùi thơm nhẹ.',
    'bánh ngọt',
    45000,
    '[{"name": "Hộp", "price": 45000}]'::jsonb,
    '["Chocolate", "Hạnh nhân"]'::jsonb,
    true
  ),
  (
    '10000000-0000-0000-0000-000000000025',
    'Bánh kem trứng dừa nướng',
    'Bánh bông lan kem trứng nướng cháy bề mặt ngọt béo thơm lừng, rắc vụn dừa sấy khô giòn bùi.',
    'bánh ngọt',
    50000,
    '[{"name": "Hộp", "price": 50000}]'::jsonb,
    '["Kem trứng", "Dừa sấy"]'::jsonb,
    true
  ),
  (
    '10000000-0000-0000-0000-000000000026',
    'Bánh crepe sầu riêng',
    'Bánh crepe sầu riêng tươi thơm lừng, béo ngậy bọc trong lớp kem whipping mượt mà vỏ dai mịn (Hộp 4 cái).',
    'bánh ngọt',
    65000,
    '[{"name": "Hộp 4 cái", "price": 65000}]'::jsonb,
    '["Sầu riêng"]'::jsonb,
    true
  ),
  (
    '10000000-0000-0000-0000-000000000027',
    'Rau câu flan cheese',
    'Lớp rau câu cà phê giòn ngọt mát lạnh ôm trọn nhân bánh flan phô mai béo ngậy đặc trưng.',
    'bánh ngọt',
    55000,
    '[{"name": "Cái", "price": 55000}]'::jsonb,
    '["Cà phê flan"]'::jsonb,
    true
  ),
  (
    '10000000-0000-0000-0000-000000000028',
    'Bánh gato flan',
    'Sự kết hợp hoàn hảo giữa lớp flan caramel ngọt ngào, béo ngậy và cốt bánh bông lan ẩm mịn.',
    'bánh ngọt',
    40000,
    '[{"name": "Cái", "price": 40000}]'::jsonb,
    '["Caramel flan"]'::jsonb,
    true
  );

INSERT INTO product_images (product_id, url, sort_order) VALUES
  ('10000000-0000-0000-0000-000000000011', '/storage/v1/object/public/product-images/f8abd31e-1a81-402b-846b-a060f048bfb7/47edd1ea-117a-4af9-a121-853fce784ad9.jpg', 0),
  ('10000000-0000-0000-0000-000000000012', '/storage/v1/object/public/product-images/e1043f4e-455b-4207-9738-ae5c6d35d11a/ea8ece0e-c88f-49d8-a259-419cabfbab7c.jpg', 0),
  ('10000000-0000-0000-0000-000000000013', '/storage/v1/object/public/product-images/4ae7c6b8-021f-4586-996c-503c999c8b81/c229ed4a-8ed1-476b-b078-2434aeca9a4d.jpg', 0),
  ('10000000-0000-0000-0000-000000000014', '/storage/v1/object/public/product-images/07010aaa-5c07-45cb-a281-b64e25cd4f2e/ee06dc81-7975-4a1b-ad48-a310e3dcf7ee.jpg', 0),
  ('10000000-0000-0000-0000-000000000014', '/storage/v1/object/public/product-images/07010aaa-5c07-45cb-a281-b64e25cd4f2e/6e175830-fae4-47a5-ad68-61e96caeaf8d.jpg', 1),
  ('10000000-0000-0000-0000-000000000015', '/storage/v1/object/public/product-images/c8162012-2014-406d-9a73-79005f8b5d0c/b23732eb-ec6c-4628-91e3-31f9b294b99c.jpg', 0),
  ('10000000-0000-0000-0000-000000000016', '/storage/v1/object/public/product-images/fa3c5bc8-6892-4936-85cd-e6168bf55d44/e580c258-f2f4-409e-b006-4bb7b4664f58.jpg', 0),
  ('10000000-0000-0000-0000-000000000017', '/storage/v1/object/public/product-images/11010bd9-d8e0-4e77-826b-0c9759d41337/b86b21db-c1f1-407a-8766-c86d93b4d554.jpg', 0),
  ('10000000-0000-0000-0000-000000000018', '/storage/v1/object/public/product-images/9fa439b6-de20-4d70-aeac-749cab3038d9/24595024-e80a-4e97-87a0-2dfe8bce9d25.jpg', 0),
  ('10000000-0000-0000-0000-000000000019', '/storage/v1/object/public/product-images/fb16fd04-2f71-42d1-8f6d-9f271f012824/444faa8c-56cc-4749-825e-8e16060f2d30.jpg', 0),
  ('10000000-0000-0000-0000-000000000020', '/storage/v1/object/public/product-images/2bef4751-ffec-44b0-9c19-bbc9ea31b976/a5485712-d9b8-4122-9547-50774f1a1c7b.jpg', 0),
  ('10000000-0000-0000-0000-000000000020', '/storage/v1/object/public/product-images/2bef4751-ffec-44b0-9c19-bbc9ea31b976/b12428f4-1870-49cd-a567-7bc98b3f2d4c.jpg', 1),
  ('10000000-0000-0000-0000-000000000021', '/storage/v1/object/public/product-images/0d0629f8-602d-4a04-bcd7-e19e29f5bb77/1cfa1071-ffde-46f0-abfe-e94ed6b70f2f.jpg', 0),
  ('10000000-0000-0000-0000-000000000022', '/storage/v1/object/public/product-images/df16ec4d-4371-4fdc-bbae-11dfcdc9feeb/ba4c9a91-9227-49b8-b14f-6ab4d6766087.jpg', 0),
  ('10000000-0000-0000-0000-000000000023', '/storage/v1/object/public/product-images/458bf2ad-9a54-4940-bdde-abf6c35d14b9/aec76ef0-ab38-4c4e-b34e-9e3aeebec9d0.jpg', 0),
  ('10000000-0000-0000-0000-000000000024', '/storage/v1/object/public/product-images/2c58cf32-c4cb-4b8c-b1ce-de10a37d25a3/2d06e863-6a7d-456d-8a85-80f9a551e594.jpg', 0),
  ('10000000-0000-0000-0000-000000000025', '/storage/v1/object/public/product-images/20f03363-8a19-414a-937e-67cc4d3aa36c/9d3b66c9-c657-4dee-8428-556dfeeaad6f.jpg', 0),
  ('10000000-0000-0000-0000-000000000026', '/storage/v1/object/public/product-images/9f5b616e-f160-4e25-bd1b-c6909f306484/b52fe046-35bf-46e3-809b-9d707745182f.jpg', 0),
  ('10000000-0000-0000-0000-000000000027', '/storage/v1/object/public/product-images/2e213149-e644-47f3-af77-98d58b670e31/772af16b-ec74-4474-bdbe-88244e8c4ee5.jpg', 0),
  ('10000000-0000-0000-0000-000000000028', '/storage/v1/object/public/product-images/e667a636-98a7-4dc7-bc1b-0d2372c82d97/33cce67e-2f11-456f-872d-a1fb3e1e7780.jpg', 0);
