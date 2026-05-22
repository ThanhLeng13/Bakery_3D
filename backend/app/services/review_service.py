"""Review service - business logic for submitting and fetching reviews.

Handles:
- Review eligibility validation (order must be delivered, within 30 days)
- Uniqueness enforcement (one review per product/customer/order)
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

        if order_result.data is None:
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

    def _check_duplicate(self, product_id: str, customer_id: str, order_id: str) -> None:
        """
        Check if a review already exists for this product/customer/order combination.

        Raises:
            ReviewDuplicateError: If a review already exists
        """
        existing = (
            self._supabase.table("reviews")
            .select("id")
            .eq("product_id", product_id)
            .eq("customer_id", customer_id)
            .eq("order_id", order_id)
            .maybe_single()
            .execute()
        )

        if existing.data is not None:
            raise ReviewDuplicateError()

    async def submit_review(
        self,
        product_id: str,
        order_id: str,
        rating: int,
        comment: str | None,
        customer: dict,
    ) -> dict:
        """
        Submit a product review.

        Args:
            product_id: UUID of the product being reviewed
            order_id: UUID of the order (must be delivered, within 30 days)
            rating: Rating 1-5
            comment: Optional comment (max 1000 chars)
            customer: Current user dict

        Returns:
            Created review dict

        Raises:
            ReviewNotEligibleError: If order is not eligible
            ReviewDuplicateError: If review already exists
            ReviewServiceError: If review creation fails
        """
        customer_id = customer["id"]

        # Validate eligibility
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

        if product_result.data is None:
            raise ReviewServiceError("Sản phẩm không tồn tại.", status_code=404)

        # Create review
        review_insert = {
            "product_id": product_id,
            "customer_id": customer_id,
            "order_id": order_id,
            "rating": rating,
            "comment": comment,
        }

        result = self._supabase.table("reviews").insert(review_insert).execute()

        if not result.data:
            raise ReviewServiceError("Không thể lưu đánh giá.", status_code=500)

        return result.data[0]

    async def get_product_reviews(
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

        # Calculate average rating
        ratings_result = (
            self._supabase.table("reviews")
            .select("rating")
            .eq("product_id", product_id)
            .execute()
        )
        ratings = [r["rating"] for r in (ratings_result.data or [])]
        average_rating = None
        if ratings:
            avg = sum(ratings) / len(ratings)
            average_rating = round(avg, 1)

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

        # Fetch customer names
        if reviews:
            customer_ids = list({r["customer_id"] for r in reviews})
            users_result = (
                self._supabase.table("users")
                .select("id, full_name")
                .in_("id", customer_ids)
                .execute()
            )
            user_map = {u["id"]: u.get("full_name", "Khách hàng") for u in (users_result.data or [])}

            for review in reviews:
                review["customer_name"] = user_map.get(review["customer_id"], "Khách hàng")
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
