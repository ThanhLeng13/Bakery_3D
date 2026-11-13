"""Contracts for the optional text written on a cake.

The text is customer-visible production instruction, so it must not be stored in
``baker_notes`` (internal staff notes) or ``ai_summary`` (assistant transcript).
These source contracts keep the dedicated migration/API/RPC path aligned without
writing to the live database.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    """Read a UTF-8 repository file relative to the project root."""
    return (ROOT / relative).read_text(encoding="utf-8")


def test_migration_adds_dedicated_column_and_rpc_argument():
    """The customer message has a dedicated nullable storage contract."""
    src = _read("backend/migrations/add_customer_message_to_orders.sql")
    assert "ADD COLUMN IF NOT EXISTS customer_message TEXT" in src
    assert "p_customer_message TEXT DEFAULT NULL" in src
    assert "customer_message" in src
    assert "char_length(customer_message) <= 200" in src


def test_checkout_field_is_optional_and_sent_in_both_order_modes():
    """Ready-made and Studio orders both preserve the optional text."""
    src = _read("frontend/src/app/checkout/page.tsx")
    assert 'id="customerMessage"' in src
    assert "maxLength={200}" in src
    assert "customer_message: customerMessage.trim() || null" in src
    assert src.count("customer_message: customerMessage.trim() || null") == 2


def test_internal_baker_notes_are_not_reused_for_customer_message():
    """Separate wording in code prevents an accidental semantic merge."""
    src = _read("frontend/src/app/checkout/page.tsx")
    message_pos = src.index('id="customerMessage"')
    nearby = src[message_pos - 800:message_pos]
    assert "baker_notes" in nearby
    assert "nội bộ" in nearby


def test_service_forwards_message_and_order_detail_returns_it():
    """Message reaches the atomic RPC and is visible in detail response."""
    src = _read("backend/app/services/order_service.py")
    assert '"p_customer_message": order_data.get("customer_message")' in src
    assert '"customer_message": order.get("customer_message")' in src


def test_baker_and_customer_order_views_render_message():
    """The person writing the cake can see exactly what the customer entered."""
    baker = _read("frontend/src/app/baker/orders/page.tsx")
    admin = _read("frontend/src/app/admin/orders/page.tsx")
    customer = _read("frontend/src/app/orders/[id]/page.tsx")
    assert "Nội dung ghi trên bánh" in baker
    assert "selectedOrder.customer_message" in baker
    assert "Nội dung ghi trên bánh" in customer
    assert "order.customer_message" in customer
    assert "Nội dung ghi trên bánh" in admin
    assert "selectedOrder.customer_message" in admin
