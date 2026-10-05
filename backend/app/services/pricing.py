"""Server-side price table for cake orders.

Why this exists
---------------
`create_order` used to trust `item["unit_price"]` sent by the browser, so anyone
could POST a cake order for 1,000 VND. The client value is now ignored.

A custom cake is not a catalogue product: the Cake Builder sends the nil UUID
below as `product_id`, because a customised cake has no row in `products`.
Its price therefore comes from the chosen size, and that table has to live on
the server as well or the client still decides what it pays.

The values mirror `SIZE_PRICES` in frontend/src/app/checkout/page.tsx and
`BASE_PRICES` in frontend/src/lib/price-calculator.ts (both tables currently
agree), so the amount the customer was shown still matches the amount charged.
Keep them in sync, or better, serve them from an endpoint.
"""

# Placeholder the Cake Builder sends instead of a real product id.
NIL_UUID = "00000000-0000-0000-0000-000000000000"

# Price of a custom cake by selected size (VND).
CAKE_SIZE_PRICES: dict[str, int] = {
    "16cm": 250_000,
    "20cm": 350_000,
    "24cm": 450_000,
    "2-tier": 650_000,
}

# Mirrors the frontend fallback `SIZE_PRICES[size] || 350000`.
DEFAULT_CAKE_PRICE = CAKE_SIZE_PRICES["20cm"]

TWO_TIER_SIZES = ("2-tier", "2 tier", "2tier")


def is_custom_cake(product_id) -> bool:
    """True when the item has no catalogue product behind it."""
    return product_id is None or str(product_id) == NIL_UUID


def normalize_size(size) -> str:
    """Normalise a size for table lookup; '' when it is missing or unusable."""
    if not isinstance(size, str):
        return ""
    return size.strip().lower()


def cake_price(size) -> int:
    """Price for a custom cake of the given size."""
    return CAKE_SIZE_PRICES.get(normalize_size(size), DEFAULT_CAKE_PRICE)


def is_two_tier(size) -> bool:
    """True when the size denotes a two-tier cake."""
    return normalize_size(size) in TWO_TIER_SIZES
