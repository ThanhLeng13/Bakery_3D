"""Tests for loyalty service."""

from unittest.mock import MagicMock
import pytest

from app.services.loyalty_service import (
    InsufficientPointsError,
    LoyaltyService,
    LoyaltyServiceError,
)

class TestLoyaltyServiceGetBalance:
    def setup_method(self):
        self.mock_supabase = MagicMock()
        self.loyalty_service = LoyaltyService(self.mock_supabase)
        self.user_id = "user-1"

    def test_get_balance_existing(self):
        self.mock_supabase.table().select().eq().maybe_single().execute.return_value = MagicMock(
            data={"user_id": self.user_id, "points": 150, "total_earned": 200, "updated_at": "2024-01-01"}
        )

        result = self.loyalty_service.get_balance(self.user_id)
        assert result["points"] == 150
        assert result["total_earned"] == 200
        assert result["available_vouchers"] == 1
        assert result["points_to_next_voucher"] == 50

    def test_get_balance_creates_new(self):
        self.mock_supabase.table().select().eq().maybe_single().execute.return_value = MagicMock(data=None)
        self.mock_supabase.table().insert().execute.return_value = MagicMock(
            data=[{"user_id": self.user_id, "points": 0, "total_earned": 0}]
        )

        result = self.loyalty_service.get_balance(self.user_id)
        assert result["points"] == 0
        assert result["points_to_next_voucher"] == 100

    def test_get_balance_exact_milestone(self):
        self.mock_supabase.table().select().eq().maybe_single().execute.return_value = MagicMock(
            data={"user_id": self.user_id, "points": 200, "total_earned": 200}
        )

        result = self.loyalty_service.get_balance(self.user_id)
        assert result["points"] == 200
        assert result["available_vouchers"] == 2
        assert result["points_to_next_voucher"] == 0


class TestLoyaltyServiceAwardPoints:
    def setup_method(self):
        self.mock_supabase = MagicMock()
        self.loyalty_service = LoyaltyService(self.mock_supabase)
        self.user_id = "user-1"

    def test_award_points_purchase(self):
        # 100k = 100 points
        pts = self.loyalty_service.award_points(self.user_id, 100000, "purchase", "ref-1")
        assert pts == 100
        self.mock_supabase.rpc.assert_called_once()
        args = self.mock_supabase.rpc.call_args[0]
        assert args[0] == "increment_loyalty_points"
        assert args[1]["p_points"] == 100
        assert args[1]["p_type"] == "purchase"

    def test_award_points_order(self):
        # 100k = 150 points for order
        pts = self.loyalty_service.award_points(self.user_id, 100000, "order", "ref-2")
        assert pts == 150
        args = self.mock_supabase.rpc.call_args[0]
        assert args[1]["p_points"] == 150

    def test_award_points_invalid_type(self):
        with pytest.raises(LoyaltyServiceError):
            self.loyalty_service.award_points(self.user_id, 100000, "invalid", "ref-3")

    def test_award_points_rpc_error(self):
        self.mock_supabase.rpc().execute.side_effect = Exception("DB Error")
        with pytest.raises(LoyaltyServiceError) as exc:
            self.loyalty_service.award_points(self.user_id, 100000, "purchase", "ref-1")
        assert "lỗi hệ thống" in exc.value.message


class TestLoyaltyServiceRedeemPoints:
    def setup_method(self):
        self.mock_supabase = MagicMock()
        self.loyalty_service = LoyaltyService(self.mock_supabase)
        self.user_id = "user-1"

    def test_redeem_points_success(self):
        self.mock_supabase.rpc().execute.return_value = MagicMock(
            data=[{"remaining_points": 50}]
        )

        result = self.loyalty_service.redeem_points(self.user_id, voucher_count=2)
        assert result["points_used"] == 200
        assert result["discount_vnd"] == 10000
        assert result["remaining_points"] == 50
        assert len(result["voucher_codes"]) == 2
        
        args = self.mock_supabase.rpc.call_args[0]
        assert args[0] == "rpc_redeem_points"
        assert args[1]["p_points_needed"] == 200

    def test_redeem_points_insufficient(self):
        self.mock_supabase.rpc().execute.side_effect = Exception("INSUFFICIENT_POINTS")
        
        # Mock get_balance for error message
        self.loyalty_service._get_or_create_balance = MagicMock(return_value={"points": 50})

        with pytest.raises(InsufficientPointsError) as exc:
            self.loyalty_service.redeem_points(self.user_id, voucher_count=1)
        
        assert exc.value.status_code == 400
        assert "Không đủ điểm" in exc.value.message
        assert "100" in exc.value.message # requested
        assert "50" in exc.value.message # available

    def test_redeem_points_invalid_count(self):
        with pytest.raises(LoyaltyServiceError) as exc:
            self.loyalty_service.redeem_points(self.user_id, voucher_count=0)
        assert "ít nhất là 1" in exc.value.message

    def test_redeem_points_max_exceeded(self):
        with pytest.raises(LoyaltyServiceError) as exc:
            self.loyalty_service.redeem_points(self.user_id, voucher_count=11)
        assert "Tối đa đổi 10" in exc.value.message
