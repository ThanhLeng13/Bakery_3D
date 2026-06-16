"""Review service - business logic for submitting and fetching reviews.

Handles:
- Review eligibility validation (optional: order must be delivered, within 30 days)
- Uniqueness enforcement (one review per product/customer, optionally scoped to order)
- Average rating calculation
"""

import math
from datetime import datetime, timezone, timedelta
from typing import Any


class ReviewServiceError(Exception):
    """Base exception for review service errors."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class ReviewNotEligibleError(ReviewServiceError):
    """Order is not eligible for review."""

    def __init__(self, reason: str):
        super().__init__(reason, status_code=403)


class ReviewDuplicateError(ReviewServiceError):
    """Review already exists for this product/customer/order combination."""

    def __init__(self):
        super().__init__(
            "Bạn đã đánh giá sản phẩm này cho đơn hàng này rồi.",
            status_code=409,
        )


class ReviewService:
    """Review service for managing product reviews in Supabase."""

    def __init__(self, supabase_client: Any):
        """Initialize with a Supabase client instance."""
        self._supabase = supabase_client

    def _check_eligibility(self, order_id: str, customer_id: str) -> dict:
        """
        Check if a customer is eligible to review a product for a given order.

        Requirements:
        - Order must exist and belong to the customer
        - Order status must be 'delivered'
        - Delivery (updated_at) must be within the last 30 days

        Returns the order dict if eligible.

        Raises:
            ReviewNotEligibleError: If order is not eligible for review
        """
        order_result = (
            self._supabase.table("orders")
            .select("id, customer_id, status, updated_at")
            .eq("id", order_id)
            .eq("customer_id", customer_id)
            .maybe_single()
            .execute()
        )

        if order_result is None or order_result.data is None:
            raise ReviewNotEligibleError(
                "Đơn hàng không tồn tại hoặc không thuộc về bạn."
            )

        order = order_result.data

        if order["status"] != "delivered":
            raise ReviewNotEligibleError(
                "Bạn chỉ có thể đánh giá đơn hàng đã được giao."
            )

        # Check within 30 days of delivery
        now = datetime.now(timezone.utc)
        updated_at = datetime.fromisoformat(order["updated_at"].replace("Z", "+00:00"))
        if (now - updated_at) > timedelta(days=30):
            raise ReviewNotEligibleError(
                "Chỉ có thể đánh giá trong vòng 30 ngày sau khi nhận hàng."
            )

        return order

    def _check_duplicate(self, product_id: str, customer_id: str, order_id: str | None) -> None:
        """
        Check if a review already exists for this product/customer combination.

        When order_id is None, checks for reviews with NULL order_id
        (product+customer uniqueness). When provided, also checks order_id.

        Raises:
            ReviewDuplicateError: If a review already exists
        """
        query = (
            self._supabase.table("reviews")
            .select("id")
            .eq("product_id", product_id)
            .eq("customer_id", customer_id)
        )
        if order_id is not None:
            query = query.eq("order_id", order_id)
        else:
            query = query.is_("order_id", "null")

        existing = query.maybe_single().execute()

        if existing is not None and existing.data is not None:
            raise ReviewDuplicateError()

    def submit_review(
        self,
        product_id: str,
        order_id: str | None,
        rating: int,
        comment: str | None,
        customer: dict,
    ) -> dict:
        """
        Submit a product review.

        Args:
            product_id: UUID of the product being reviewed
            order_id: UUID of the order (optional). When provided, validates
                      that the order is delivered and within 30 days.
                      When None, skips order eligibility check.
            rating: Rating 1-5
            comment: Optional comment (max 1000 chars)
            customer: Current user dict

        Returns:
            Created review dict

        Raises:
            ReviewNotEligibleError: If order is not eligible (only when order_id provided)
            ReviewDuplicateError: If review already exists
            ReviewServiceError: If review creation fails
        """
        customer_id = customer["id"]

        # Validate eligibility only when order_id is provided
        if order_id is not None:
            self._check_eligibility(order_id, customer_id)

        # Check duplicate
        self._check_duplicate(product_id, customer_id, order_id)

        # Verify product exists
        product_result = (
            self._supabase.table("products")
            .select("id, name")
            .eq("id", product_id)
            .eq("is_active", True)
            .maybe_single()
            .execute()
        )

        if product_result is None or product_result.data is None:
            raise ReviewServiceError("Sản phẩm không tồn tại.", status_code=404)

        # Create review — omit order_id key entirely when None to avoid NULL issues
        review_insert: dict = {
            "product_id": product_id,
            "customer_id": customer_id,
            "rating": rating,
        }
        if order_id is not None:
            review_insert["order_id"] = order_id
        if comment is not None:
            review_insert["comment"] = comment

        try:
            result = self._supabase.table("reviews").insert(review_insert).execute()
        except Exception as e:
            err_str = str(e).lower()
            if "unique" in err_str or "duplicate" in err_str:
                raise ReviewDuplicateError() from e
            raise ReviewServiceError("Không thể lưu đánh giá. Đã xảy ra lỗi hệ thống.", status_code=500) from e

        if not result.data:
            raise ReviewServiceError("Không thể lưu đánh giá.", status_code=500)

        return result.data[0]

    def get_product_reviews(
        self,
        product_id: str,
        page: int = 1,
        page_size: int = 10,
    ) -> dict:
        """
        Get paginated reviews for a product.

        Args:
            product_id: UUID of the product
            page: Page number (1-indexed)
            page_size: Items per page (default 10)

        Returns:
            Dict with reviews list, pagination, average_rating, review_count
        """
        # Count total reviews
        count_result = (
            self._supabase.table("reviews")
            .select("id", count="exact")
            .eq("product_id", product_id)
            .execute()
        )
        total_items = count_result.count if count_result.count is not None else 0

        # Get pre-aggregated review stats from database view
        stats_result = (
            self._supabase.table("product_review_stats")
            .select("review_count, average_rating")
            .eq("product_id", product_id)
            .maybe_single()
            .execute()
        )
        stats = stats_result.data if (stats_result and stats_result.data) else {}
        average_rating = float(stats["average_rating"]) if stats.get("average_rating") is not None else None

        # Pagination
        total_pages = math.ceil(total_items / page_size) if total_items > 0 else 0
        offset = (page - 1) * page_size

        # Fetch reviews with customer name
        reviews_result = (
            self._supabase.table("reviews")
            .select("id, rating, comment, created_at, customer_id")
            .eq("product_id", product_id)
            .order("created_at", desc=True)
            .range(offset, offset + page_size - 1)
            .execute()
        )

        reviews = reviews_result.data or []

        # Fetch customer names — use service role client so RLS doesn't block
        if reviews:
            customer_ids = list({r["customer_id"] for r in reviews})
            users_result = (
                self._supabase.table("users")
                .select("id, full_name, email")
                .in_("id", customer_ids)
                .execute()
            )

            def _display_name(u: dict) -> str:
                name = u.get("full_name") or ""
                if name.strip():
                    return name.strip()
                return "Khách hàng"

            user_map = {u["id"]: _display_name(u) for u in (users_result.data or [])}

            for review in reviews:
                review["customer_name"] = user_map.get(review["customer_id"], "Người dùng")
                del review["customer_id"]  # Don't expose customer IDs

        return {
            "reviews": reviews,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total_items,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1,
            },
            "average_rating": average_rating,
            "review_count": total_items,
        }
