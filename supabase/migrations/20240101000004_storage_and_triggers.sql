-- ============================================================
-- Cake Shop AI Web - Storage Buckets and Triggers
-- ============================================================

-- ============================================================
-- STORAGE BUCKET FOR PRODUCT IMAGES
-- ============================================================

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'product-images',
  'product-images',
  true,
  5242880, -- 5MB in bytes
  ARRAY['image/jpeg', 'image/png', 'image/webp']
);

-- Storage policies for product-images bucket

-- Anyone can read product images (public bucket)
CREATE POLICY storage_product_images_select ON storage.objects
  FOR SELECT
  USING (bucket_id = 'product-images');

-- Admin can upload product images
CREATE POLICY storage_product_images_insert ON storage.objects
  FOR INSERT
  WITH CHECK (
    bucket_id = 'product-images'
    AND get_user_role(auth.uid()) = 'admin'
  );

-- Admin can update product images
CREATE POLICY storage_product_images_update ON storage.objects
  FOR UPDATE
  USING (
    bucket_id = 'product-images'
    AND get_user_role(auth.uid()) = 'admin'
  );

-- Admin can delete product images
CREATE POLICY storage_product_images_delete ON storage.objects
  FOR DELETE
  USING (
    bucket_id = 'product-images'
    AND get_user_role(auth.uid()) = 'admin'
  );

-- ============================================================
-- TRIGGERS FOR updated_at
-- ============================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_users_updated_at
  BEFORE UPDATE ON users
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_products_updated_at
  BEFORE UPDATE ON products
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_orders_updated_at
  BEFORE UPDATE ON orders
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_chat_sessions_updated_at
  BEFORE UPDATE ON chat_sessions
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- TRIGGER FOR ORDER STATUS HISTORY AUTO-INSERT
-- ============================================================

CREATE OR REPLACE FUNCTION record_order_status_change()
RETURNS TRIGGER AS $$
BEGIN
  IF OLD.status IS DISTINCT FROM NEW.status THEN
    INSERT INTO order_status_history (order_id, old_status, new_status, changed_by)
    VALUES (NEW.id, OLD.status, NEW.status, auth.uid());
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trigger_order_status_change
  AFTER UPDATE OF status ON orders
  FOR EACH ROW
  EXECUTE FUNCTION record_order_status_change();

-- ============================================================
-- TRIGGER FOR CHAT MESSAGE COUNT
-- ============================================================

CREATE OR REPLACE FUNCTION increment_chat_message_count()
RETURNS TRIGGER AS $$
BEGIN
  UPDATE chat_sessions
  SET message_count = message_count + 1
  WHERE id = NEW.session_id;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trigger_chat_message_count
  AFTER INSERT ON chat_messages
  FOR EACH ROW
  EXECUTE FUNCTION increment_chat_message_count();
