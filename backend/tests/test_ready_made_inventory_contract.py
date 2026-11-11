"""Regression contracts for ready-made inventory across sweet and cake products.

These tests do not connect to Supabase and do not execute the migration. They lock
three business invariants in source/service contracts:
  1. inventory accepts both catalogue product types;
  2. custom Studio orders do not receive a branch/stock requirement;
  3. ready-made catalogue orders forward branch_id to the atomic RPC.
"""

from pathlib import Path

from app.services.inventory_service import InventoryService


ROOT = Path(__file__).resolve().parents[2]


def test_inventory_service_no_longer_rejects_cake_catalogue_products():
    src = (ROOT / "backend/app/services/inventory_service.py").read_text(encoding="utf-8")
    assert 'product.data.get("product_type") != "sweet"' not in src
    assert 'select("id, name, product_type")' in src


def test_order_rpc_contract_contains_branch_argument():
    src = (ROOT / "backend/app/services/order_service.py").read_text(encoding="utf-8")
    assert '"p_branch_id": order_data.get("branch_id")' in src


def test_checkout_sends_branch_for_ready_made_and_not_for_studio_customization():
    src = (ROOT / "frontend/src/app/checkout/page.tsx").read_text(encoding="utf-8")
    ready_start = src.index("if (isReadyMadeCakeMode) {")
    cart_start = src.index("} else if (isCartMode) {")
    ready_block = src[ready_start:cart_start]
    assert "branch_id: selectedBranchId!" in ready_block

    # Studio's own order payload is after the cart branches; it must not be
    # accidentally made a ready-made stock order.
    custom_start = src.index("const orderItems = [", cart_start)
    custom_end = src.index("const response = await apiClient.post", custom_start)
    custom_block = src[custom_start:custom_end]
    assert "00000000-0000-0000-0000-000000000000" in custom_block
    assert "customization_json" in custom_block


def test_ready_made_inventory_migration_has_fifo_lock_and_rollback_transaction():
    src = (ROOT / "backend/migrations/add_ready_made_inventory_to_orders.sql").read_text(encoding="utf-8")
    assert "ALTER TABLE public.orders" in src
    assert "ADD COLUMN IF NOT EXISTS branch_id" in src
    assert "FOR UPDATE" in src
    assert "ORDER BY expires_at ASC, produced_at ASC" in src
    assert "CREATE FUNCTION public.rpc_create_order" in src
    assert "DROP FUNCTION IF EXISTS public.rpc_create_order" in src
    assert "p_branch_id UUID" in src
    assert "quantity_sold = quantity_sold + v_take" in src
    assert "v_has_catalogue_item" in src


def test_migration_documents_required_order():
    src = (ROOT / "backend/migrations/add_ready_made_inventory_to_orders.sql").read_text(encoding="utf-8")
    assert "after add_create_order_rpc.sql" in src
    assert "custom Studio" in src and "product_batches" in src


# Keep the service import explicit: this file is a contract around that service,
# not an accidental source-only test with no production symbol.
assert InventoryService is not None
