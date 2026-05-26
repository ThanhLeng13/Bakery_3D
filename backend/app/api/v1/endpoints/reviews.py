"""Review API endpoints.

Endpoints:
- POST /api/v1/reviews - Submit review (Customer)
- GET /api/v1/products/{id}/reviews - Get product reviews (paginated)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.dependencies import get_current_user, require_customer
from app.services.review_service import (
    ReviewDuplicateError,
    ReviewNotEligibleError,
    ReviewService,
    ReviewServiceError,
)

router = APIRouter()


class SubmitReviewRequest(BaseModel):
    """Request body for submitting a review."""
    product_id: str = Field(..., description="UUID of the product being reviewed")
    order_id: str = Field(..., description="UUID of the delivered order")
    rating: int = Field(..., ge=1, le=5, description="Rating 1-5")
    comment: str | None = Field(
        default=None,
        max_length=1000,
        description="Optional review comment (max 1000 chars)",
    )


def _get_supabase_client():
    """Get Supabase client instance."""
    from supabase import create_client
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


def _get_review_service() -> ReviewService:
    """Create ReviewService with Supabase client."""
    client = _get_supabase_client()
    return ReviewService(client)


@router.post("/", status_code=201)
async def submit_review(
    body: SubmitReviewRequest,
    customer: dict = Depends(require_customer),
):
    """
    Submit a product review (Customer only).

    Eligibility requirements:
    - Order must belong to the customer
    - Order status must be 'delivered'
    - Delivery must be within the last 30 days
    - One review per (product_id, customer_id, order_id)

    Rating must be 1-5. Comment is optional, max 1000 chars.
    """
    review_service = _get_review_service()

    try:
        result = await review_service.submit_review(
            product_id=body.product_id,
            order_id=body.order_id,
            rating=body.rating,
            comment=body.comment,
            customer=customer,
        )
        return result
    except ReviewNotEligibleError as e:
        raise HTTPException(status_code=403, detail=e.message)
    except ReviewDuplicateError as e:
        raise HTTPException(status_code=409, detail=e.message)
    except ReviewServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/{product_id}/product-reviews")
async def get_product_reviews(
    product_id: str,
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=10, ge=1, le=50, description="Items per page"),
):
    """
    Get paginated reviews for a product (public endpoint).

    Returns reviews sorted newest first with customer names,
    average rating (1 decimal), and review count.
    """
    review_service = _get_review_service()

    try:
        result = await review_service.get_product_reviews(
            product_id=product_id,
            page=page,
            page_size=page_size,
        )
        return result
    except ReviewServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
