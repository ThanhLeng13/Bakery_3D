"""Catalog service - business logic for product queries.

Handles product listing with pagination, filtering, and detail retrieval.
Only active products are returned for customer-facing endpoints.
"""

import math
from typing import Any, Optional

from app.core.config import settings
from app.utils.image_url import format_image_url


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

    async def list_products(
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
        # Build base query for counting
        count_query = (
            self._supabase.table("products")
            .select("id", count="exact")
            .eq("is_active", True)
        )

        if category:
            count_query = count_query.eq("category", category)

        count_result = count_query.execute()
        total_items = count_result.count if count_result.count is not None else 0

        # Calculate pagination
        total_pages = math.ceil(total_items / page_size) if total_items > 0 else 0
        offset = (page - 1) * page_size

        # Build data query
        data_query = (
            self._supabase.table("products")
            .select("id, name, description, category, base_price, created_at, product_images(url, sort_order), reviews(rating)")
            .eq("is_active", True)
            .order("created_at", desc=True)
            .range(offset, offset + page_size - 1)
        )

        if category:
            data_query = data_query.eq("category", category)

        data_result = data_query.execute()
        products_data = data_result.data or []

        # Fetch first image for each product and review aggregates
        products = []
        for product in products_data:
            product_id = product["id"]

            # Get first image (sorted by sort_order) from embedded relation
            images = product.get("product_images") or []
            if images:
                images_sorted = sorted(images, key=lambda x: x.get("sort_order", 0))
                image_url = format_image_url(images_sorted[0].get("url"))
            else:
                image_url = None

            # Get average rating and review count from embedded relation
            reviews = product.get("reviews") or []
            review_count = len(reviews)
            average_rating = None
            if review_count > 0:
                avg = sum(r["rating"] for r in reviews) / review_count
                average_rating = round(avg, 1)

            # Truncate description to 100 chars for list view
            description = product.get("description") or ""
            if len(description) > 100:
                description = description[:100]

            products.append({
                "id": product_id,
                "name": product["name"],
                "description": description,
                "category": product["category"],
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

    async def get_product_detail(self, product_id: str) -> dict:
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
        # Fetch product
        product_result = (
            self._supabase.table("products")
            .select("*")
            .eq("id", product_id)
            .eq("is_active", True)
            .maybe_single()
            .execute()
        )

        if product_result is None or product_result.data is None:
            raise ProductNotFoundError(product_id)

        product = product_result.data

        # Fetch all images sorted by sort_order
        images_result = (
            self._supabase.table("product_images")
            .select("id, url, sort_order")
            .eq("product_id", product_id)
            .order("sort_order", desc=False)
            .execute()
        )
        images = images_result.data or []
        for img in images:
            if "url" in img:
                img["url"] = format_image_url(img["url"])

        # Get average rating and review count
        review_result = (
            self._supabase.table("reviews")
            .select("rating")
            .eq("product_id", product_id)
            .execute()
        )
        reviews = review_result.data or []
        review_count = len(reviews)
        average_rating = None
        if review_count > 0:
            avg = sum(r["rating"] for r in reviews) / review_count
            average_rating = round(avg, 1)

        raw_sizes = product.get("sizes") or []
        sizes = []
        for s in raw_sizes:
            if isinstance(s, dict):
                sizes.append(s)
            elif isinstance(s, str):
                sizes.append({"name": s, "price": product["base_price"]})

        raw_flavors = product.get("flavors") or []
        flavors = []
        for f in raw_flavors:
            if isinstance(f, dict):
                flavors.append(f)
            elif isinstance(f, str):
                flavors.append({"name": f, "additional_cost": 0})

        return {
            "id": product["id"],
            "name": product["name"],
            "description": product.get("description"),
            "category": product["category"],
            "base_price": product["base_price"],
            "sizes": sizes,
            "flavors": flavors,
            "is_active": product["is_active"],
            "images": images,
            "average_rating": average_rating,
            "review_count": review_count,
            "created_at": product["created_at"],
            "updated_at": product["updated_at"],
        }
