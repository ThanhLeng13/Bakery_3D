-- Migration: Create cake_options table
-- Run this in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS cake_options (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type        TEXT NOT NULL CHECK (type IN ('size', 'flavor', 'topping', 'color')),
    name        TEXT NOT NULL,
    label       TEXT NOT NULL,           -- Display label (Vietnamese)
    price_modifier INTEGER NOT NULL DEFAULT 0,  -- Additional price in VND (can be 0)
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order  INTEGER NOT NULL DEFAULT 0,
    icon        TEXT,                    -- Emoji or icon string (optional)
    hex_color   TEXT
        CHECK (
            -- color type: hex_color is required and must be a valid hex
            (type = 'color' AND hex_color IS NOT NULL AND hex_color ~ '^#[0-9A-Fa-f]{6}$')
            OR
            -- non-color types: hex_color must be null
            (type != 'color' AND hex_color IS NULL)
        ),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Business-key uniqueness: prevent duplicate (type, name) pairs
    CONSTRAINT cake_options_type_name_unique UNIQUE (type, name)
);

-- Index for faster filtering by type
CREATE INDEX IF NOT EXISTS idx_cake_options_type ON cake_options(type);
CREATE INDEX IF NOT EXISTS idx_cake_options_active ON cake_options(is_active);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_cake_options_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_cake_options_updated_at
    BEFORE UPDATE ON cake_options
    FOR EACH ROW EXECUTE FUNCTION update_cake_options_updated_at();

-- Seed initial data (matching current hardcoded values in OptionsPanel.tsx)
-- Sizes
INSERT INTO cake_options (type, name, label, price_modifier, sort_order) VALUES
    ('size', '4 inch',  '4 inch (1-4 người)',  0,      1),
    ('size', '6 inch',  '6 inch (4-8 người)',  100000, 2),
    ('size', '8 inch',  '8 inch (8-12 người)', 200000, 3),
    ('size', '10 inch', '10 inch (12+ người)', 350000, 4),
    ('size', '2 tầng',  '2 tầng (đặc biệt)',   500000, 5)
ON CONFLICT (type, name) DO NOTHING;

-- Flavors
INSERT INTO cake_options (type, name, label, price_modifier, sort_order) VALUES
    ('flavor', 'vanilla',    'Vani',         0,     1),
    ('flavor', 'chocolate',  'Socola',       0,     2),
    ('flavor', 'strawberry', 'Dâu tây',      0,     3),
    ('flavor', 'matcha',     'Matcha',       30000, 4),
    ('flavor', 'tiramisu',   'Tiramisu',     50000, 5),
    ('flavor', 'red_velvet', 'Red Velvet',   50000, 6)
ON CONFLICT (type, name) DO NOTHING;

-- Toppings
INSERT INTO cake_options (type, name, label, price_modifier, sort_order, icon) VALUES
    ('topping', 'flowers',          'Hoa',              50000,  1, '🌸'),
    ('topping', 'fruits',           'Trái cây',         70000,  2, '🍓'),
    ('topping', 'chocolate drip',   'Chocolate drip',   40000,  3, '🍫'),
    ('topping', 'sprinkles',        'Sprinkles',        20000,  4, '✨'),
    ('topping', 'macarons',         'Macarons',         80000,  5, '🧁'),
    ('topping', 'text',             'Chữ viết',         30000,  6, '✍️')
ON CONFLICT (type, name) DO NOTHING;

-- Colors (cream colors) — hex_color required for type='color'
INSERT INTO cake_options (type, name, label, price_modifier, sort_order, hex_color) VALUES
    ('color', 'pink',      'Hồng',    0, 1, '#F4A7B9'),
    ('color', 'white',     'Trắng',   0, 2, '#FFFDF5'),
    ('color', 'chocolate', 'Socola',  0, 3, '#7B4F2E'),
    ('color', 'matcha',    'Matcha',  0, 4, '#8DB48E'),
    ('color', 'vanilla',   'Vani',    0, 5, '#F5E6C8'),
    ('color', 'lavender',  'Lavender',0, 6, '#C8B8E8')
ON CONFLICT (type, name) DO NOTHING;

-- RLS Policies
ALTER TABLE cake_options ENABLE ROW LEVEL SECURITY;

-- Anyone can read active options (for public Cake Builder)
CREATE POLICY "cake_options_public_read" ON cake_options
    FOR SELECT USING (is_active = TRUE);

-- NOTE: The service_role client (used by admin endpoints) bypasses RLS
-- automatically, so no additional policy is needed. A FOR ALL TO PUBLIC
-- policy would be a security vulnerability and is intentionally omitted.
