"""Review API endpoints.

Endpoints:
- POST /api/v1/reviews - Submit review (Customer)
- GET /api/v1/products/{id}/reviews - Get product reviews (paginated)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from app.core.dependencies import get_current_user, require_customer, security_scheme, get_supabase_client
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
    order_id: str | None = Field(
        default=None,
        description="UUID of the delivered order (optional)",
    )
    rating: int = Field(..., ge=1, le=5, description="Rating 1-5")
    comment: str | None = Field(
        default=None,
        max_length=1000,
        description="Optional review comment (max 1000 chars)",
    )


def _get_review_service(token: str | None = None, use_service_role: bool = False) -> ReviewService:
    """Create ReviewService with Supabase client."""
    client = get_supabase_client(token, use_service_role=use_service_role)
    return ReviewService(client)


@router.post("/reviews", status_code=201)
def submit_review(
    body: SubmitReviewRequest,
    customer: dict = Depends(require_customer),
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
):
    """
    Submit a product review (Customer only).

    Rating must be 1-5. Comment is optional, max 1000 chars.
    order_id is optional — when omitted, review is submitted without order link.
    """
    token = credentials.credentials if credentials else None
    # Use service role to bypass RLS — auth is already validated by require_customer
    review_service = _get_review_service(token, use_service_role=True)

    try:
        result = review_service.submit_review(
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
    except Exception as e:
        import logging
        logging.error(f"Unexpected error submitting review: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while processing your request") from e


@router.get("/products/{product_id}/reviews")
def get_product_reviews(
    product_id: str,
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=10, ge=1, le=50, description="Items per page"),
):
    """
    Get paginated reviews for a product (public endpoint).

    Returns reviews sorted newest first with customer names,
    average rating (1 decimal), and review count.
    """
    review_service = _get_review_service(use_service_role=True)

    try:
        result = review_service.get_product_reviews(
            product_id=product_id,
            page=page,
            page_size=page_size,
        )
        return result
    except ReviewServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
