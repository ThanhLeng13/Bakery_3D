"""Catalog service - business logic for product queries.

Handles product listing with pagination, filtering, and detail retrieval.
Only active products are returned for customer-facing endpoints.
"""

import logging
import math
from typing import Any, Optional

from app.core.config import settings
from app.utils.image_url import format_image_url

logger = logging.getLogger(__name__)


def _coerce_cost(value: Any) -> int:
    """Safely coerce a flavor's additional_cost to a non-negative int.

    Handles every pathological DB value:
    - None / missing           → 0
    - Empty string ""          → 0
    - Numeric string "5000"    → 5000
    - Float 4999.9             → 4999
    - Non-numeric string "abc" → 0
    - float("inf") / "inf"     → 0  (OverflowError caught)
    - NaN                      → 0  (ValueError from int(float("nan")) is caught)
    """
    if value is None:
        return 0
    try:
        # float() first to handle strings like "5000.5"; int() truncates.
        # OverflowError: int(float("inf")) — infinity cannot convert to int.
        # ValueError:    int(float("nan")) — NaN cannot convert to int.
        # TypeError:     non-numeric types that float() rejects.
        return max(0, int(float(value)))
    except (ValueError, TypeError, OverflowError):
        return 0


class CatalogServiceError(Exception):
    """Base exception for catalog service errors."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class ProductNotFoundError(CatalogServiceError):
    """Product not found or inactive."""

    def __init__(self, product_id: str):
        super().__init__(
            f"Product not found: {product_id}",
            status_code=404,
        )


class CatalogService:
    """Catalog service for querying products from Supabase."""

    def __init__(self, supabase_client: Any):
        """Initialize with a Supabase client instance."""
        self._supabase = supabase_client

    def list_products(
        self,
        page: int = 1,
        page_size: int = 20,
        category: Optional[str] = None,
    ) -> dict:
        """
        List active products with pagination and optional category filter.

        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page (default 20)
            category: Optional category filter

        Returns:
            Dict with products list and pagination metadata
        """
        # Single query: count + data in one round-trip
        offset = (page - 1) * page_size

        data_query = (
            self._supabase.table("products")
            .select(
                "id, name, description, category, product_type, base_price, created_at,"
                " product_images(url, sort_order),"
                " product_review_stats(review_count, average_rating)",
                count="exact",
            )
            .eq("is_active", True)
        )

        if category:
            data_query = data_query.eq("category", category)

        data_query = data_query.order("created_at", desc=True).range(offset, offset + page_size - 1)

        data_result = data_query.execute()
        products_data = data_result.data or []
        total_items = data_result.count if data_result.count is not None else 0

        # Calculate pagination
        total_pages = math.ceil(total_items / page_size) if total_items > 0 else 0

        # Build product list with first image and pre-aggregated review stats
        products = []
        for product in products_data:
            product_id = product["id"]

            # Get first image (sorted by sort_order) from embedded relation
            images = product.get("product_images") or []
            if images:
                images_sorted = sorted(images, key=lambda x: x.get("sort_order") or 0)
                image_url = format_image_url(images_sorted[0].get("url"))
            else:
                image_url = None

            # Get pre-aggregated review stats from embedded view
            stats_list = product.get("product_review_stats") or []
            if stats_list:
                stats = stats_list[0] if isinstance(stats_list, list) else stats_list
                review_count = stats.get("review_count", 0) or 0
                avg_raw = stats.get("average_rating")
                average_rating = float(avg_raw) if avg_raw is not None else None
            else:
                review_count = 0
                average_rating = None

            # Truncate description to 100 chars for list view
            description = product.get("description") or ""
            if len(description) > 100:
                description = description[:100]

            products.append({
                "id": product_id,
                "name": product["name"],
                "description": description,
                "category": product["category"],
                "product_type": product.get("product_type") or "sweet",
                "base_price": product["base_price"],
                "image_url": image_url,
                "average_rating": average_rating,
                "review_count": review_count,
                "created_at": product["created_at"],
            })

        pagination = {
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1,
        }

        return {
            "products": products,
            "pagination": pagination,
        }

    def get_product_detail(self, product_id: str) -> dict:
        """
        Get full product detail by ID.

        Only returns active products. Returns 404 if product not found or inactive.

        Args:
            product_id: UUID string of the product

        Returns:
            Dict with full product detail including images, sizes, flavors, reviews

        Raises:
            ProductNotFoundError: If product not found or inactive
        """
        # Single query: product + images + review_stats in one round-trip
        product_result = (
            self._supabase.table("products")
            .select(
                "*,"
                " product_images(id, url, sort_order),"
                " product_review_stats(review_count, average_rating)"
            )
            .eq("id", product_id)
            .eq("is_active", True)
            .maybe_single()
            .execute()
        )

        if product_result is None or product_result.data is None:
            raise ProductNotFoundError(product_id)

        product = product_result.data

        # Extract and format images (already sorted by DB via PostgREST)
        raw_images = sorted(
            product.get("product_images") or [],
            key=lambda x: x.get("sort_order") or 0,
        )
        images = [
            {"id": img["id"], "url": format_image_url(img["url"]), "sort_order": img.get("sort_order") or 0}
            for img in raw_images
        ]

        # Extract review stats from embedded view
        stats_list = product.get("product_review_stats") or []
        stats = (stats_list[0] if isinstance(stats_list, list) and stats_list else stats_list) or {}
        review_count = stats.get("review_count", 0) or 0
        avg_raw = stats.get("average_rating")
        average_rating = float(avg_raw) if avg_raw is not None else None

        raw_sizes = product.get("sizes") or []
        sizes = []
        for s in raw_sizes:
            if isinstance(s, dict):
                sizes.append(s)
            elif isinstance(s, str):
                sizes.append({"name": s, "price": product["base_price"]})


        # Normalize flavors.
        # DB may store: a JSON array of strings, an array of dicts, a bare
        # string (legacy), or null.  Guard every case so we never iterate a
        # string character-by-character.
        raw = product.get("flavors")
        if raw is None:
            raw_flavors: list = []
        elif isinstance(raw, str):
            # Bare string → treat as a single flavor entry
            logger.warning(
                "Product %s: flavors stored as a bare string, wrapping in list",
                product.get("id"),
            )
            raw_flavors = [raw]
        elif isinstance(raw, list):
            raw_flavors = raw
        else:
            logger.warning(
                "Product %s: unexpected flavors type %s (%r) — treating as empty",
                product.get("id"),
                type(raw).__name__,
                raw,
            )
            raw_flavors = []

        normalized_flavors = []
        for f in raw_flavors:
            if isinstance(f, str):
                normalized_flavors.append({"name": f, "additional_cost": 0})
            elif isinstance(f, dict):
                normalized_flavors.append({
                    "name": f.get("name", ""),
                    "additional_cost": _coerce_cost(f.get("additional_cost")),
                })
            else:
                logger.warning(
                    "Unexpected flavor entry type for product %s: got %s (%r) — skipping",
                    product.get("id"),
                    type(f).__name__,
                    f,
                )

        return {
            "id": product["id"],
            "name": product["name"],
            "description": product.get("description"),
            "category": product["category"],
            "product_type": product.get("product_type") or "sweet",
            "base_price": product["base_price"],
            "sizes": sizes,
            "flavors": normalized_flavors,
            "is_active": product["is_active"],
            "images": images,
            "average_rating": average_rating,
            "review_count": review_count,
            "created_at": product["created_at"],
            "updated_at": product["updated_at"],
        }
