-- ============================================================
-- Cake Shop AI Web - Row Level Security (RLS) Policies
-- ============================================================
-- Enforces access control at the database level
-- Roles: customer, admin, baker
-- ============================================================

-- Enable RLS on all tables
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

-- ============================================================
-- Helper function to get current user role
-- ============================================================

CREATE OR REPLACE FUNCTION get_user_role(user_id UUID)
RETURNS user_role AS $$
  SELECT role FROM users WHERE id = user_id;
$$ LANGUAGE sql SECURITY DEFINER STABLE;

-- ============================================================
-- USERS POLICIES
-- ============================================================

-- Users can read their own profile
CREATE POLICY users_select_own ON users
  FOR SELECT
  USING (auth.uid() = id);

-- Admin can read all users
CREATE POLICY users_select_admin ON users
  FOR SELECT
  USING (get_user_role(auth.uid()) = 'admin');

-- Users can update their own profile
CREATE POLICY users_update_own ON users
  FOR UPDATE
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

-- Allow insert during registration (service role handles this)
CREATE POLICY users_insert ON users
  FOR INSERT
  WITH CHECK (auth.uid() = id);

-- ============================================================
-- PRODUCTS POLICIES
-- ============================================================

-- Anyone can read active products (public catalog)
CREATE POLICY products_select_active ON products
  FOR SELECT
  USING (is_active = true);

-- Admin can read all products (including inactive)
CREATE POLICY products_select_admin ON products
  FOR SELECT
  USING (get_user_role(auth.uid()) = 'admin');

-- Admin can create products
CREATE POLICY products_insert_admin ON products
  FOR INSERT
  WITH CHECK (get_user_role(auth.uid()) = 'admin');

-- Admin can update products
CREATE POLICY products_update_admin ON products
  FOR UPDATE
  USING (get_user_role(auth.uid()) = 'admin')
  WITH CHECK (get_user_role(auth.uid()) = 'admin');

-- ============================================================
-- PRODUCT IMAGES POLICIES
-- ============================================================

-- Anyone can read product images (public)
CREATE POLICY product_images_select ON product_images
  FOR SELECT
  USING (true);

-- Admin can manage product images
CREATE POLICY product_images_insert_admin ON product_images
  FOR INSERT
  WITH CHECK (get_user_role(auth.uid()) = 'admin');

CREATE POLICY product_images_update_admin ON product_images
  FOR UPDATE
  USING (get_user_role(auth.uid()) = 'admin');

CREATE POLICY product_images_delete_admin ON product_images
  FOR DELETE
  USING (get_user_role(auth.uid()) = 'admin');

-- ============================================================
-- ORDERS POLICIES
-- ============================================================

-- Customers can read their own orders
CREATE POLICY orders_select_own ON orders
  FOR SELECT
  USING (auth.uid() = customer_id);

-- Admin can read all orders
CREATE POLICY orders_select_admin ON orders
  FOR SELECT
  USING (get_user_role(auth.uid()) = 'admin');

-- Baker can read confirmed and in_production orders
CREATE POLICY orders_select_baker ON orders
  FOR SELECT
  USING (
    get_user_role(auth.uid()) = 'baker'
    AND status IN ('confirmed', 'in_production')
  );

-- Customers can create orders
CREATE POLICY orders_insert_customer ON orders
  FOR INSERT
  WITH CHECK (auth.uid() = customer_id);

-- Admin can update orders (status changes, etc.)
CREATE POLICY orders_update_admin ON orders
  FOR UPDATE
  USING (get_user_role(auth.uid()) = 'admin');

-- Baker can update orders (status changes, baker_notes)
CREATE POLICY orders_update_baker ON orders
  FOR UPDATE
  USING (
    get_user_role(auth.uid()) = 'baker'
    AND status IN ('confirmed', 'in_production')
  );

-- ============================================================
-- ORDER ITEMS POLICIES
-- ============================================================

-- Customers can read their own order items
CREATE POLICY order_items_select_own ON order_items
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM orders
      WHERE orders.id = order_items.order_id
      AND orders.customer_id = auth.uid()
    )
  );

-- Admin can read all order items
CREATE POLICY order_items_select_admin ON order_items
  FOR SELECT
  USING (get_user_role(auth.uid()) = 'admin');

-- Baker can read order items for their visible orders
CREATE POLICY order_items_select_baker ON order_items
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM orders
      WHERE orders.id = order_items.order_id
      AND orders.status IN ('confirmed', 'in_production')
      AND get_user_role(auth.uid()) = 'baker'
    )
  );

-- Customers can create order items (when placing an order)
CREATE POLICY order_items_insert_customer ON order_items
  FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM orders
      WHERE orders.id = order_items.order_id
      AND orders.customer_id = auth.uid()
    )
  );

-- ============================================================
-- CAKE CUSTOMIZATIONS POLICIES
-- ============================================================

-- Customers can read their own customizations
CREATE POLICY cake_customizations_select_own ON cake_customizations
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM orders
      WHERE orders.id = cake_customizations.order_id
      AND orders.customer_id = auth.uid()
    )
  );

-- Admin can read all customizations
CREATE POLICY cake_customizations_select_admin ON cake_customizations
  FOR SELECT
  USING (get_user_role(auth.uid()) = 'admin');

-- Baker can read customizations for their visible orders
CREATE POLICY cake_customizations_select_baker ON cake_customizations
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM orders
      WHERE orders.id = cake_customizations.order_id
      AND orders.status IN ('confirmed', 'in_production')
      AND get_user_role(auth.uid()) = 'baker'
    )
  );

-- Customers can create customizations
CREATE POLICY cake_customizations_insert_customer ON cake_customizations
  FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM orders
      WHERE orders.id = cake_customizations.order_id
      AND orders.customer_id = auth.uid()
    )
  );

-- ============================================================
-- ORDER STATUS HISTORY POLICIES
-- ============================================================

-- Customers can read status history for their orders
CREATE POLICY order_status_history_select_own ON order_status_history
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM orders
      WHERE orders.id = order_status_history.order_id
      AND orders.customer_id = auth.uid()
    )
  );

-- Admin can read and create status history
CREATE POLICY order_status_history_select_admin ON order_status_history
  FOR SELECT
  USING (get_user_role(auth.uid()) = 'admin');

CREATE POLICY order_status_history_insert_admin ON order_status_history
  FOR INSERT
  WITH CHECK (get_user_role(auth.uid()) = 'admin');

-- Baker can read and create status history for their orders
CREATE POLICY order_status_history_select_baker ON order_status_history
  FOR SELECT
  USING (
    get_user_role(auth.uid()) = 'baker'
    AND EXISTS (
      SELECT 1 FROM orders
      WHERE orders.id = order_status_history.order_id
      AND orders.status IN ('confirmed', 'in_production')
    )
  );

CREATE POLICY order_status_history_insert_baker ON order_status_history
  FOR INSERT
  WITH CHECK (get_user_role(auth.uid()) = 'baker');

-- ============================================================
-- CHAT SESSIONS POLICIES
-- ============================================================

-- Customers can read their own chat sessions
CREATE POLICY chat_sessions_select_own ON chat_sessions
  FOR SELECT
  USING (auth.uid() = customer_id);

-- Customers can create chat sessions
CREATE POLICY chat_sessions_insert_own ON chat_sessions
  FOR INSERT
  WITH CHECK (auth.uid() = customer_id);

-- Customers can update their own chat sessions (message_count)
CREATE POLICY chat_sessions_update_own ON chat_sessions
  FOR UPDATE
  USING (auth.uid() = customer_id)
  WITH CHECK (auth.uid() = customer_id);

-- Admin can read all chat sessions
CREATE POLICY chat_sessions_select_admin ON chat_sessions
  FOR SELECT
  USING (get_user_role(auth.uid()) = 'admin');

-- ============================================================
-- CHAT MESSAGES POLICIES
-- ============================================================

-- Customers can read their own chat messages
CREATE POLICY chat_messages_select_own ON chat_messages
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM chat_sessions
      WHERE chat_sessions.id = chat_messages.session_id
      AND chat_sessions.customer_id = auth.uid()
    )
  );

-- Customers can create chat messages
CREATE POLICY chat_messages_insert_own ON chat_messages
  FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM chat_sessions
      WHERE chat_sessions.id = chat_messages.session_id
      AND chat_sessions.customer_id = auth.uid()
    )
  );

-- Admin can read all chat messages
CREATE POLICY chat_messages_select_admin ON chat_messages
  FOR SELECT
  USING (get_user_role(auth.uid()) = 'admin');

-- ============================================================
-- REVIEWS POLICIES
-- ============================================================

-- Anyone can read reviews (public)
CREATE POLICY reviews_select ON reviews
  FOR SELECT
  USING (true);

-- Customers can create reviews for their own delivered orders
CREATE POLICY reviews_insert_customer ON reviews
  FOR INSERT
  WITH CHECK (
    auth.uid() = customer_id
    AND EXISTS (
      SELECT 1 FROM orders
      WHERE orders.id = reviews.order_id
      AND orders.customer_id = auth.uid()
      AND orders.status = 'delivered'
    )
  );

-- Admin can manage reviews
CREATE POLICY reviews_delete_admin ON reviews
  FOR DELETE
  USING (get_user_role(auth.uid()) = 'admin');
