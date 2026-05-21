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
    '["16cm", "20cm", "24cm"]',
    '["dark chocolate", "chocolate-orange", "chocolate-mint"]',
    true
  ),
  (
    '10000000-0000-0000-0000-000000000005',
    'Bánh Kem Trái Cây Nhiệt Đới',
    'Bánh kem tươi mát với các loại trái cây nhiệt đới: xoài, passion fruit, dừa. Hoàn hảo cho mùa hè.',
    'bánh ngọt',
    220000,
    '["16cm", "20cm", "24cm"]',
    '["tropical", "mango", "coconut"]',
    false -- inactive product for testing
  );
