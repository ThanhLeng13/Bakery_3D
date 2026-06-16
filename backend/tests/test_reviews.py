"""Tests for review service."""

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
import pytest

from app.services.review_service import (
    ReviewDuplicateError,
    ReviewNotEligibleError,
    ReviewService,
    ReviewServiceError,
)


class TestReviewServiceCheckEligibility:
    def setup_method(self):
        self.mock_supabase = MagicMock()
        self.review_service = ReviewService(self.mock_supabase)
        self.now = datetime.now(timezone.utc)

    def test_eligibility_success(self):
        recent_delivery = (self.now - timedelta(days=10)).isoformat()
        self.mock_supabase.table().select().eq().eq().maybe_single().execute.return_value = MagicMock(
            data={"id": "order-1", "customer_id": "cust-1", "status": "delivered", "updated_at": recent_delivery}
        )

        order = self.review_service._check_eligibility("order-1", "cust-1")
        assert order["id"] == "order-1"

    def test_eligibility_order_not_found(self):
        self.mock_supabase.table().select().eq().eq().maybe_single().execute.return_value = MagicMock(data=None)

        with pytest.raises(ReviewNotEligibleError) as exc:
            self.review_service._check_eligibility("order-1", "cust-1")
        assert "không tồn tại" in exc.value.message

    def test_eligibility_not_delivered(self):
        self.mock_supabase.table().select().eq().eq().maybe_single().execute.return_value = MagicMock(
            data={"id": "order-1", "customer_id": "cust-1", "status": "in_production", "updated_at": self.now.isoformat()}
        )

        with pytest.raises(ReviewNotEligibleError) as exc:
            self.review_service._check_eligibility("order-1", "cust-1")
        assert "đã được giao" in exc.value.message

    def test_eligibility_over_30_days(self):
        old_delivery = (self.now - timedelta(days=35)).isoformat()
        self.mock_supabase.table().select().eq().eq().maybe_single().execute.return_value = MagicMock(
            data={"id": "order-1", "customer_id": "cust-1", "status": "delivered", "updated_at": old_delivery}
        )

        with pytest.raises(ReviewNotEligibleError) as exc:
            self.review_service._check_eligibility("order-1", "cust-1")
        assert "30 ngày" in exc.value.message


class TestReviewServiceCheckDuplicate:
    def setup_method(self):
        self.mock_supabase = MagicMock()
        self.review_service = ReviewService(self.mock_supabase)

    def test_no_duplicate(self):
        self.mock_supabase.table().select().eq().eq().eq().maybe_single().execute.return_value = MagicMock(data=None)
        
        # Should not raise
        self.review_service._check_duplicate("prod-1", "cust-1", "order-1")

    def test_duplicate_exists(self):
        self.mock_supabase.table().select().eq().eq().eq().maybe_single().execute.return_value = MagicMock(
            data={"id": "rev-1"}
        )

        with pytest.raises(ReviewDuplicateError):
            self.review_service._check_duplicate("prod-1", "cust-1", "order-1")

    def test_no_duplicate_none_order(self):
        self.mock_supabase.table().select().eq().eq().is_().maybe_single().execute.return_value = MagicMock(data=None)
        
        # Should not raise
        self.review_service._check_duplicate("prod-1", "cust-1", None)


class TestReviewServiceSubmitReview:
    def setup_method(self):
        self.mock_supabase = MagicMock()
        self.review_service = ReviewService(self.mock_supabase)
        self.customer = {"id": "cust-1"}
    def test_submit_review_success_with_order(self):
        # Mock eligibility (delivered recently)
        self.mock_supabase.table().select().eq().eq().maybe_single().execute.return_value = MagicMock(
            data={"id": "order-1", "customer_id": "cust-1", "status": "delivered", "updated_at": datetime.now(timezone.utc).isoformat()}
        )
        
        # Mock duplicate check (none)
        # We need to mock table calls properly if they are chained. 
        # Since _check_eligibility and _check_duplicate also call table(), we'll patch them for simplicity in this integration test.
        self.review_service._check_eligibility = MagicMock()
        self.review_service._check_duplicate = MagicMock()

        # Mock product verification
        self.mock_supabase.table().select().eq().eq().maybe_single().execute.return_value = MagicMock(
            data={"id": "prod-1", "name": "Cake"}
        )

        # Mock insert
        self.mock_supabase.table().insert().execute.return_value = MagicMock(
            data=[{"id": "rev-1", "product_id": "prod-1", "rating": 5}]
        )

        result = self.review_service.submit_review(
            product_id="prod-1",
            order_id="order-1",
            rating=5,
            comment="Ngon",
            customer=self.customer
        )

        assert result["id"] == "rev-1"
        self.review_service._check_eligibility.assert_called_once_with("order-1", "cust-1")
        self.review_service._check_duplicate.assert_called_once_with("prod-1", "cust-1", "order-1")
    def test_submit_review_success_without_order(self):
        self.review_service._check_eligibility = MagicMock()
        self.review_service._check_duplicate = MagicMock()

        # Mock product verification
        self.mock_supabase.table().select().eq().eq().maybe_single().execute.return_value = MagicMock(
            data={"id": "prod-1", "name": "Cake"}
        )

        # Mock insert
        self.mock_supabase.table().insert().execute.return_value = MagicMock(
            data=[{"id": "rev-2", "product_id": "prod-1", "rating": 5}]
        )

        result = self.review_service.submit_review(
            product_id="prod-1",
            order_id=None,
            rating=5,
            comment="Ngon",
            customer=self.customer
        )

        assert result["id"] == "rev-2"
        self.review_service._check_eligibility.assert_not_called()
        self.review_service._check_duplicate.assert_called_once_with("prod-1", "cust-1", None)
    def test_submit_review_product_not_found(self):
        self.review_service._check_eligibility = MagicMock()
        self.review_service._check_duplicate = MagicMock()
        
        # Product not found
        self.mock_supabase.table().select().eq().eq().maybe_single().execute.return_value = MagicMock(data=None)

        with pytest.raises(ReviewServiceError) as exc:
            self.review_service.submit_review("prod-X", "order-1", 5, None, self.customer)
        assert "Sản phẩm không tồn tại" in exc.value.message


class TestReviewServiceGetReviews:
    def setup_method(self):
        self.mock_supabase = MagicMock()
        self.review_service = ReviewService(self.mock_supabase)
    def test_get_product_reviews(self):
        # Mock count
        count_mock = MagicMock()
        count_mock.count = 15
        self.mock_supabase.table().select().eq().execute.return_value = count_mock

        # Mock stats
        self.mock_supabase.table().select().eq().maybe_single().execute.return_value = MagicMock(
            data={"review_count": 15, "average_rating": 4.5}
        )

        # Mock reviews
        self.mock_supabase.table().select().eq().order().range().execute.return_value = MagicMock(
            data=[
                {"id": "rev-1", "rating": 5, "comment": "Good", "created_at": "2024-01-01", "customer_id": "cust-1"},
                {"id": "rev-2", "rating": 4, "comment": "Ok", "created_at": "2024-01-02", "customer_id": "cust-2"}
            ]
        )

        # Mock users
        self.mock_supabase.table().select().in_().execute.return_value = MagicMock(
            data=[
                {"id": "cust-1", "full_name": "Nguyen A", "email": "a@x.com"},
                {"id": "cust-2", "full_name": "", "email": "b@y.com"},
            ]
        )

        result = self.review_service.get_product_reviews("prod-1", page=1, page_size=10)

        assert result["review_count"] == 15
        assert result["average_rating"] == 4.5
        assert result["pagination"]["total_pages"] == 2
        assert len(result["reviews"]) == 2
        assert result["reviews"][0]["customer_name"] == "Nguyen A"
        assert result["reviews"][1]["customer_name"] == "b"
        assert "customer_id" not in result["reviews"][0]
