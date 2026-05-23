-- ============================================================
-- CAKE SHOP AI WEB - ALL MIGRATIONS COMBINED
-- Run this in Supabase Dashboard > SQL Editor
-- ============================================================

-- ============================================================
-- PART 1: INITIAL SCHEMA
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TYPE user_role AS ENUM ('customer', 'admin', 'baker');
CREATE TYPE order_status AS ENUM ('pending', 'confirmed', 'in_production', 'ready', 'delivered');
CREATE TYPE chat_message_role AS ENUM ('user', 'assistant');

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email VARCHAR(254) NOT NULL,
  full_name VARCHAR(100) NOT NULL,
  phone VARCHAR(10),
  role user_role NOT NULL DEFAULT 'customer',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT users_email_unique UNIQUE (email),
  CONSTRAINT users_phone_format CHECK (phone IS NULL OR phone ~ '^\d{10}$')
);

CREATE TABLE products (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name VARCHAR(200) NOT NULL,
  description TEXT,
  category VARCHAR(100) NOT NULL,
  base_price INTEGER NOT NULL,
  sizes JSONB DEFAULT '[]'::jsonb,
  flavors JSONB DEFAULT '[]'::jsonb,
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT products_name_length CHECK (char_length(name) >= 1 AND char_length(name) <= 200),
  CONSTRAINT products_base_price_range CHECK (base_price >= 1000 AND base_price <= 999999999)
);

CREATE TABLE product_images (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  url VARCHAR(500) NOT NULL,
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE orders (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  customer_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  status order_status NOT NULL DEFAULT 'pending',
  total_price INTEGER NOT NULL,
  pickup_date TIMESTAMPTZ NOT NULL,
  customer_name VARCHAR(100) NOT NULL,
  customer_phone VARCHAR(10) NOT NULL,
  customer_email VARCHAR(254),
  ai_summary TEXT,
  baker_notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT orders_customer_phone_format CHECK (customer_phone ~ '^\d{10}$'),
  CONSTRAINT orders_baker_notes_length CHECK (baker_notes IS NULL OR char_length(baker_notes) <= 500)
);

CREATE TABLE order_items (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  product_id UUID NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
  size VARCHAR(50),
  flavor VARCHAR(100),
  quantity INTEGER NOT NULL DEFAULT 1,
  unit_price INTEGER NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE cake_customizations (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  order_item_id UUID REFERENCES order_items(id) ON DELETE CASCADE,
  customization_json JSONB NOT NULL,
  preview_image_url VARCHAR(500),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE order_status_history (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  old_status order_status,
  new_status order_status NOT NULL,
  changed_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE chat_sessions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  customer_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  message_count INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT chat_sessions_message_count_limit CHECK (message_count >= 0 AND message_count <= 20)
);

CREATE TABLE chat_messages (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
  role chat_message_role NOT NULL,
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE reviews (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  customer_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  rating INTEGER NOT NULL,
  comment TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT reviews_rating_range CHECK (rating >= 1 AND rating <= 5),
  CONSTRAINT reviews_comment_length CHECK (comment IS NULL OR char_length(comment) <= 1000),
  CONSTRAINT reviews_unique_per_product_order UNIQUE (product_id, customer_id, order_id)
);

-- ============================================================
-- PART 2: INDEXES
-- ============================================================

CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_products_is_active ON products(is_active);
CREATE INDEX idx_products_created_at ON products(created_at DESC);
CREATE INDEX idx_products_active_category ON products(is_active, category) WHERE is_active = true;
CREATE INDEX idx_product_images_product_id ON product_images(product_id);
CREATE INDEX idx_product_images_sort_order ON product_images(product_id, sort_order);
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_pickup_date ON orders(pickup_date);
CREATE INDEX idx_orders_created_at ON orders(created_at DESC);
CREATE INDEX idx_orders_status_pickup ON orders(status, pickup_date ASC);
CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_order_items_product_id ON order_items(product_id);
CREATE INDEX idx_cake_customizations_order_id ON cake_customizations(order_id);
CREATE INDEX idx_cake_customizations_order_item_id ON cake_customizations(order_item_id);
CREATE INDEX idx_order_status_history_order_id ON order_status_history(order_id);
CREATE INDEX idx_order_status_history_changed_at ON order_status_history(changed_at DESC);
CREATE INDEX idx_chat_sessions_customer_id ON chat_sessions(customer_id);
CREATE INDEX idx_chat_sessions_updated_at ON chat_sessions(updated_at DESC);
CREATE INDEX idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX idx_chat_messages_created_at ON chat_messages(session_id, created_at ASC);
CREATE INDEX idx_reviews_product_id ON reviews(product_id);
CREATE INDEX idx_reviews_customer_id ON reviews(customer_id);
CREATE INDEX idx_reviews_order_id ON reviews(order_id);
CREATE INDEX idx_reviews_created_at ON reviews(product_id, created_at DESC);

-- ============================================================
-- PART 3: RLS POLICIES
-- ============================================================

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE product_images ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE cake_customizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE order_status_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE reviews ENABLE ROW LEVEL SECURITY;

CREATE OR REPLACE FUNCTION get_user_role(user_id UUID)
RETURNS user_role AS $$
  SELECT role FROM users WHERE id = user_id;
$$ LANGUAGE sql SECURITY DEFINER STABLE;

CREATE POLICY users_select_own ON users FOR SELECT USING (auth.uid() = id);
CREATE POLICY users_select_admin ON users FOR SELECT USING (get_user_role(auth.uid()) = 'admin');
CREATE POLICY users_update_own ON users FOR UPDATE USING (auth.uid() = id) WITH CHECK (auth.uid() = id);
CREATE POLICY users_insert ON users FOR INSERT WITH CHECK (auth.uid() = id);

CREATE POLICY products_select_active ON products FOR SELECT USING (is_active = true);
CREATE POLICY products_select_admin ON products FOR SELECT USING (get_user_role(auth.uid()) = 'admin');
CREATE POLICY products_insert_admin ON products FOR INSERT WITH CHECK (get_user_role(auth.uid()) = 'admin');
CREATE POLICY products_update_admin ON products FOR UPDATE USING (get_user_role(auth.uid()) = 'admin') WITH CHECK (get_user_role(auth.uid()) = 'admin');

CREATE POLICY product_images_select ON product_images FOR SELECT USING (true);
CREATE POLICY product_images_insert_admin ON product_images FOR INSERT WITH CHECK (get_user_role(auth.uid()) = 'admin');
CREATE POLICY product_images_update_admin ON product_images FOR UPDATE USING (get_user_role(auth.uid()) = 'admin');
CREATE POLICY product_images_delete_admin ON product_images FOR DELETE USING (get_user_role(auth.uid()) = 'admin');

CREATE POLICY orders_select_own ON orders FOR SELECT USING (auth.uid() = customer_id);
CREATE POLICY orders_select_admin ON orders FOR SELECT USING (get_user_role(auth.uid()) = 'admin');
CREATE POLICY orders_select_baker ON orders FOR SELECT USING (get_user_role(auth.uid()) = 'baker' AND status IN ('confirmed', 'in_production'));
CREATE POLICY orders_insert_customer ON orders FOR INSERT WITH CHECK (auth.uid() = customer_id);
CREATE POLICY orders_update_admin ON orders FOR UPDATE USING (get_user_role(auth.uid()) = 'admin');
CREATE POLICY orders_update_baker ON orders FOR UPDATE USING (get_user_role(auth.uid()) = 'baker' AND status IN ('confirmed', 'in_production'));

CREATE POLICY order_items_select_own ON order_items FOR SELECT USING (EXISTS (SELECT 1 FROM orders WHERE orders.id = order_items.order_id AND orders.customer_id = auth.uid()));
CREATE POLICY order_items_select_admin ON order_items FOR SELECT USING (get_user_role(auth.uid()) = 'admin');
CREATE POLICY order_items_select_baker ON order_items FOR SELECT USING (EXISTS (SELECT 1 FROM orders WHERE orders.id = order_items.order_id AND orders.status IN ('confirmed', 'in_production') AND get_user_role(auth.uid()) = 'baker'));
CREATE POLICY order_items_insert_customer ON order_items FOR INSERT WITH CHECK (EXISTS (SELECT 1 FROM orders WHERE orders.id = order_items.order_id AND orders.customer_id = auth.uid()));

CREATE POLICY cake_customizations_select_own ON cake_customizations FOR SELECT USING (EXISTS (SELECT 1 FROM orders WHERE orders.id = cake_customizations.order_id AND orders.customer_id = auth.uid()));
CREATE POLICY cake_customizations_select_admin ON cake_customizations FOR SELECT USING (get_user_role(auth.uid()) = 'admin');
CREATE POLICY cake_customizations_select_baker ON cake_customizations FOR SELECT USING (EXISTS (SELECT 1 FROM orders WHERE orders.id = cake_customizations.order_id AND orders.status IN ('confirmed', 'in_production') AND get_user_role(auth.uid()) = 'baker'));
CREATE POLICY cake_customizations_insert_customer ON cake_customizations FOR INSERT WITH CHECK (EXISTS (SELECT 1 FROM orders WHERE orders.id = cake_customizations.order_id AND orders.customer_id = auth.uid()));

CREATE POLICY order_status_history_select_own ON order_status_history FOR SELECT USING (EXISTS (SELECT 1 FROM orders WHERE orders.id = order_status_history.order_id AND orders.customer_id = auth.uid()));
CREATE POLICY order_status_history_select_admin ON order_status_history FOR SELECT USING (get_user_role(auth.uid()) = 'admin');
CREATE POLICY order_status_history_insert_admin ON order_status_history FOR INSERT WITH CHECK (get_user_role(auth.uid()) = 'admin');
CREATE POLICY order_status_history_select_baker ON order_status_history FOR SELECT USING (get_user_role(auth.uid()) = 'baker' AND EXISTS (SELECT 1 FROM orders WHERE orders.id = order_status_history.order_id AND orders.status IN ('confirmed', 'in_production')));
CREATE POLICY order_status_history_insert_baker ON order_status_history FOR INSERT WITH CHECK (get_user_role(auth.uid()) = 'baker');

CREATE POLICY chat_sessions_select_own ON chat_sessions FOR SELECT USING (auth.uid() = customer_id);
CREATE POLICY chat_sessions_insert_own ON chat_sessions FOR INSERT WITH CHECK (auth.uid() = customer_id);
CREATE POLICY chat_sessions_update_own ON chat_sessions FOR UPDATE USING (auth.uid() = customer_id) WITH CHECK (auth.uid() = customer_id);
CREATE POLICY chat_sessions_select_admin ON chat_sessions FOR SELECT USING (get_user_role(auth.uid()) = 'admin');

CREATE POLICY chat_messages_select_own ON chat_messages FOR SELECT USING (EXISTS (SELECT 1 FROM chat_sessions WHERE chat_sessions.id = chat_messages.session_id AND chat_sessions.customer_id = auth.uid()));
CREATE POLICY chat_messages_insert_own ON chat_messages FOR INSERT WITH CHECK (EXISTS (SELECT 1 FROM chat_sessions WHERE chat_sessions.id = chat_messages.session_id AND chat_sessions.customer_id = auth.uid()));
CREATE POLICY chat_messages_select_admin ON chat_messages FOR SELECT USING (get_user_role(auth.uid()) = 'admin');

CREATE POLICY reviews_select ON reviews FOR SELECT USING (true);
CREATE POLICY reviews_insert_customer ON reviews FOR INSERT WITH CHECK (auth.uid() = customer_id AND EXISTS (SELECT 1 FROM orders WHERE orders.id = reviews.order_id AND orders.customer_id = auth.uid() AND orders.status = 'delivered'));
CREATE POLICY reviews_delete_admin ON reviews FOR DELETE USING (get_user_role(auth.uid()) = 'admin');

-- ============================================================
-- PART 4: STORAGE & TRIGGERS
-- ============================================================

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES ('product-images', 'product-images', true, 5242880, ARRAY['image/jpeg', 'image/png', 'image/webp']);

CREATE POLICY storage_product_images_select ON storage.objects FOR SELECT USING (bucket_id = 'product-images');
CREATE POLICY storage_product_images_insert ON storage.objects FOR INSERT WITH CHECK (bucket_id = 'product-images' AND get_user_role(auth.uid()) = 'admin');
CREATE POLICY storage_product_images_update ON storage.objects FOR UPDATE USING (bucket_id = 'product-images' AND get_user_role(auth.uid()) = 'admin');
CREATE POLICY storage_product_images_delete ON storage.objects FOR DELETE USING (bucket_id = 'product-images' AND get_user_role(auth.uid()) = 'admin');

CREATE OR REPLACE FUNCTION update_updated_at_column() RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trigger_products_updated_at BEFORE UPDATE ON products FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trigger_orders_updated_at BEFORE UPDATE ON orders FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trigger_chat_sessions_updated_at BEFORE UPDATE ON chat_sessions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE FUNCTION record_order_status_change() RETURNS TRIGGER AS $$ BEGIN IF OLD.status IS DISTINCT FROM NEW.status THEN INSERT INTO order_status_history (order_id, old_status, new_status, changed_by) VALUES (NEW.id, OLD.status, NEW.status, auth.uid()); END IF; RETURN NEW; END; $$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trigger_order_status_change AFTER UPDATE OF status ON orders FOR EACH ROW EXECUTE FUNCTION record_order_status_change();

CREATE OR REPLACE FUNCTION increment_chat_message_count() RETURNS TRIGGER AS $$ BEGIN UPDATE chat_sessions SET message_count = message_count + 1 WHERE id = NEW.session_id; RETURN NEW; END; $$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trigger_chat_message_count AFTER INSERT ON chat_messages FOR EACH ROW EXECUTE FUNCTION increment_chat_message_count();

-- ============================================================
-- PART 5: SEED DATA (Sample products for testing)
-- ============================================================

INSERT INTO products (name, description, category, base_price, sizes, flavors, is_active) VALUES
('Bánh kem socola sinh nhật', 'Bánh kem socola đậm đà với lớp ganache mượt mà, trang trí hoa tươi', 'bánh âu', 350000, '[{"name": "16cm", "price": 250000}, {"name": "20cm", "price": 350000}, {"name": "24cm", "price": 450000}]'::jsonb, '["Socola", "Socola đen", "Socola trắng"]'::jsonb, true),
('Bánh kem matcha', 'Bánh kem trà xanh Nhật Bản với kem whipped cream nhẹ nhàng', 'bánh âu', 380000, '[{"name": "16cm", "price": 280000}, {"name": "20cm", "price": 380000}, {"name": "24cm", "price": 480000}]'::jsonb, '["Matcha", "Matcha đậm", "Matcha-Socola"]'::jsonb, true),
('Bánh kem vanilla classic', 'Bánh kem vanilla truyền thống với buttercream mịn màng', 'bánh âu', 300000, '[{"name": "16cm", "price": 200000}, {"name": "20cm", "price": 300000}, {"name": "24cm", "price": 400000}, {"name": "2-tier", "price": 650000}]'::jsonb, '["Vanilla", "Vanilla-Dâu", "Vanilla-Caramel"]'::jsonb, true),
('Bánh kem 2 tầng hoa hồng', 'Bánh kem 2 tầng sang trọng trang trí hoa hồng buttercream', 'bánh âu', 750000, '[{"name": "2-tier", "price": 750000}]'::jsonb, '["Vanilla", "Socola", "Red Velvet"]'::jsonb, true),
('Cheesecake Red Velvet', 'Lớp bánh red velvet mềm mịn xen kẽ kem phô mai béo ngậy trong hũ tiện lợi.', 'bánh ngọt', 35000, '[{"name": "Hộp", "price": 35000}]'::jsonb, '["Red Velvet", "Phô mai"]'::jsonb, true),
('Bánh tiramisu truyền thống', 'Tiramisu Ý truyền thống thơm hương cà phê espresso và lớp kem mascarpone béo ngậy, phủ cacao và bột trà xanh.', 'bánh ngọt', 60000, '[{"name": "Hộp", "price": 60000}]'::jsonb, '["Cà phê", "Trà xanh"]'::jsonb, true),
('Bánh tiramisu gấu', 'Tiramisu thơm ngon tạo hình chú gấu dễ thương, phủ bột cacao mịn màng.', 'bánh ngọt', 55000, '[{"name": "Hộp", "price": 55000}]'::jsonb, '["Cà phê", "Socola"]'::jsonb, true),
('Bánh cheese tươi', 'Bánh kem sữa phô mai tươi mềm mịn, ngọt thanh mát lạnh đựng trong hũ square tiện dụng.', 'bánh ngọt', 60000, '[{"name": "Hộp", "price": 60000}]'::jsonb, '["Phô mai"]'::jsonb, true),
('Bánh phomai sợi dẻo', 'Bánh phô mai nướng với những sợi phô mai dai dẻo thơm ngậy trên mặt.', 'bánh ngọt', 55000, '[{"name": "Hộp", "price": 55000}]'::jsonb, '["Phô mai"]'::jsonb, true),
('Bánh tart trứng', 'Bánh tart trứng thơm lừng với vỏ ngàn lớp giòn tan và nhân kem trứng nướng mềm mịn (Hộp 3 cái).', 'bánh ngọt', 40000, '[{"name": "Hộp 3 cái", "price": 40000}]'::jsonb, '["Kem trứng"]'::jsonb, true),
('Bánh kem cốm dẻo', 'Hương vị cốm dẻo thơm mát truyền thống kết hợp kem whipped cream béo ngọt nhẹ nhàng.', 'bánh ngọt', 60000, '[{"name": "Hộp", "price": 60000}]'::jsonb, '["Cốm dẻo"]'::jsonb, true),
('Bánh khoai lang phô mai', 'Bánh khoai lang nướng bùi dẻo nhân phô mai kéo sợi thơm ngậy tuyệt hảo (Hộp 2 cái).', 'bánh ngọt', 60000, '[{"name": "Hộp 2 cái", "price": 60000}]'::jsonb, '["Khoai lang", "Phô mai"]'::jsonb, true),
('Bánh mousse chanh dây', 'Mousse chanh dây chua ngọt tươi mát, lớp thạch vàng óng mượt mà cùng cốt bánh mềm ẩm.', 'bánh ngọt', 50000, '[{"name": "Hộp", "price": 50000}]'::jsonb, '["Chanh dây"]'::jsonb, true),
('Bánh Dark Oreo', 'Bánh kem oreo cookies & cream giòn bùi thơm lừng vụn bánh oreo đậm đà.', 'bánh ngọt', 60000, '[{"name": "Hộp", "price": 60000}]'::jsonb, '["Oreo", "Cream"]'::jsonb, true),
('Bánh phô mai cháy', 'Basque Burnt Cheesecake nướng cháy xém bề mặt thơm bùi, nhân phô mai tan chảy béo ngậy tuyệt hảo.', 'bánh ngọt', 35000, '[{"name": "Cái", "price": 35000}]'::jsonb, '["Phô mai"]'::jsonb, true),
('Bánh su kem', 'Bánh su kem choux pastry mini nhân kem custard sữa ngọt mát mịn màng (Hộp 9 cái).', 'bánh ngọt', 50000, '[{"name": "Hộp 9 cái", "price": 50000}]'::jsonb, '["Vanilla custard"]'::jsonb, true),
('Bánh chuối nướng nước dừa', 'Bánh chuối nướng dẻo ngọt, thơm đậm đà kết hợp nước cốt dừa béo ngậy.', 'bánh ngọt', 45000, '[{"name": "Hộp", "price": 45000}]'::jsonb, '["Chuối nướng", "Cốt dừa"]'::jsonb, true),
('Bánh Brownie', 'Brownie chocolate fudge đậm vị đắng ngọt, rắc hạnh nhân lát giòn bùi thơm nhẹ.', 'bánh ngọt', 45000, '[{"name": "Hộp", "price": 45000}]'::jsonb, '["Chocolate", "Hạnh nhân"]'::jsonb, true),
('Bánh kem trứng dừa nướng', 'Bánh bông lan kem trứng nướng cháy bề mặt ngọt béo thơm lừng, rắc vụn dừa sấy khô giòn bùi.', 'bánh ngọt', 50000, '[{"name": "Hộp", "price": 50000}]'::jsonb, '["Kem trứng", "Dừa sấy"]'::jsonb, true),
('Bánh crepe sầu riêng', 'Bánh crepe sầu riêng tươi thơm lừng, béo ngậy bọc trong lớp kem whipping mượt mà vỏ dai mịn (Hộp 4 cái).', 'bánh ngọt', 65000, '[{"name": "Hộp 4 cái", "price": 65000}]'::jsonb, '["Sầu riêng"]'::jsonb, true),
('Rau câu flan cheese', 'Lớp rau câu cà phê giòn ngọt mát lạnh ôm trọn nhân bánh flan phô mai béo ngậy đặc trưng.', 'bánh ngọt', 55000, '[{"name": "Cái", "price": 55000}]'::jsonb, '["Cà phê flan"]'::jsonb, true),
('Bánh gato flan', 'Sự kết hợp hoàn hảo giữa lớp flan caramel ngọt ngào, béo ngậy và cốt bánh bông lan ẩm mịn.', 'bánh ngọt', 40000, '[{"name": "Cái", "price": 40000}]'::jsonb, '["Caramel flan"]'::jsonb, true);
