"""Tests for inventory service.

Tests cover:
- Public endpoints for getting stock.
- Baker actions for adding and updating batches.
- Deducting stock with optimistic locking.
"""

from datetime import date, datetime, timedelta
from unittest.mock import MagicMock
import pytest

from app.services.inventory_service import (
    BatchNotFoundError,
    InsufficientStockError,
    InventoryService,
    InventoryServiceError,
)

class TestInventoryServicePublic:
    def setup_method(self):
        self.mock_supabase = MagicMock()
        self.inventory_service = InventoryService(self.mock_supabase)
        self.today = date.today().isoformat()
        self.future_date = (date.today() + timedelta(days=10)).isoformat()

    def test_get_product_stock_success(self):
        self.mock_supabase.table().select().eq().eq().gte().order().execute.return_value = MagicMock(
            data=[
                {
                    "id": "batch-1",
                    "quantity": 10,
                    "quantity_sold": 2,
                    "produced_at": self.today,
                    "expires_at": self.future_date,
                },
                {
                    "id": "batch-2",
                    "quantity": 5,
                    "quantity_sold": 5,
                    "produced_at": self.today,
                    "expires_at": self.future_date,
                }
            ]
        )
        
        result = self.inventory_service.get_product_stock("prod-1")
        assert result["total_available"] == 8
        assert result["product_id"] == "prod-1"
        assert len(result["batches"]) == 1
        assert result["batches"][0]["id"] == "batch-1"
        assert result["expires_soonest"] == self.future_date

    def test_get_stock_by_branch(self):
        # Mock active branches
        self.mock_supabase.table().select().eq().order().execute.return_value = MagicMock(
            data=[
                {"id": "branch-1", "name": "Branch 1", "address": "Address 1"}
            ]
        )
        
        # Mock batches
        self.mock_supabase.table().select().eq().eq().gte().order().execute.return_value = MagicMock(
            data=[
                {
                    "id": "batch-1",
                    "quantity": 10,
                    "quantity_sold": 0,
                    "expires_at": self.future_date,
                    "branch_id": "branch-1",
                    "branches": {"id": "branch-1", "name": "Branch 1", "address": "Address 1"}
                },
                {
                    "id": "batch-2",
                    "quantity": 5,
                    "quantity_sold": 0,
                    "expires_at": self.future_date,
                    "branch_id": None,
                    "branches": None
                }
            ]
        )
        
        result = self.inventory_service.get_stock_by_branch("prod-1")
        assert result["total_available"] == 15
        assert len(result["branches"]) == 2  # Branch 1 + Kho chung
        
        branch_1 = next(b for b in result["branches"] if b["branch_id"] == "branch-1")
        assert branch_1["quantity_available"] == 10
        
        kho_chung = next(b for b in result["branches"] if b["branch_id"] is None)
        assert kho_chung["quantity_available"] == 5


class TestInventoryServiceBaker:
    def setup_method(self):
        self.mock_supabase = MagicMock()
        self.inventory_service = InventoryService(self.mock_supabase)
        self.today = date.today().isoformat()
        self.future_date = (date.today() + timedelta(days=10)).isoformat()
        self.baker = {"id": "baker-1"}

    def test_add_batch_success(self):
        # Mock product type sweet
        self.mock_supabase.table().select().eq().eq().maybe_single().execute.return_value = MagicMock(
            data={"id": "prod-1", "name": "Bánh", "product_type": "sweet"}
        )
        
        # Mock insert success
        self.mock_supabase.table().insert().execute.return_value = MagicMock(
            data=[{"id": "new-batch-1"}]
        )
        
        result = self.inventory_service.add_batch(
            product_id="prod-1",
            quantity=10,
            produced_at=self.today,
            expires_at=self.future_date,
            notes="New batch",
            branch_id=None,
            baker=self.baker
        )
        assert result["id"] == "new-batch-1"

    def test_add_batch_invalid_quantity(self):
        with pytest.raises(InventoryServiceError) as exc:
            self.inventory_service.add_batch(
                product_id="prod-1",
                quantity=0,
                produced_at=self.today,
                expires_at=self.future_date,
                notes=None,
                branch_id=None,
                baker=self.baker
            )
        assert "Số lượng phải lớn hơn 0" in exc.value.message

    def test_add_batch_invalid_product_type(self):
        self.mock_supabase.table().select().eq().eq().maybe_single().execute.return_value = MagicMock(
            data={"id": "prod-1", "name": "Bánh", "product_type": "custom"}
        )
        with pytest.raises(InventoryServiceError) as exc:
            self.inventory_service.add_batch(
                product_id="prod-1",
                quantity=10,
                produced_at=self.today,
                expires_at=self.future_date,
                notes=None,
                branch_id=None,
                baker=self.baker
            )
        assert "Chỉ bánh ngọt" in exc.value.message

    def test_update_batch_success(self):
        self.mock_supabase.table().select().eq().maybe_single().execute.return_value = MagicMock(
            data={
                "id": "batch-1",
                "quantity": 10,
                "quantity_sold": 2,
                "produced_at": self.today,
                "expires_at": self.future_date,
            }
        )
        
        self.mock_supabase.table().update().eq().execute.return_value = MagicMock(
            data=[{"id": "batch-1", "quantity": 15, "quantity_sold": 2}]
        )
        
        result = self.inventory_service.update_batch("batch-1", {"quantity": 15}, self.baker)
        assert result["quantity"] == 15
        assert result["quantity_available"] == 13

    def test_update_batch_reduce_below_sold_fails(self):
        self.mock_supabase.table().select().eq().maybe_single().execute.return_value = MagicMock(
            data={
                "id": "batch-1",
                "quantity": 10,
                "quantity_sold": 5,
                "produced_at": self.today,
                "expires_at": self.future_date,
            }
        )
        
        with pytest.raises(InventoryServiceError) as exc:
            self.inventory_service.update_batch("batch-1", {"quantity": 4}, self.baker)
        assert "Không thể giảm số lượng xuống 4" in exc.value.message


class TestInventoryServicePurchase:
    def setup_method(self):
        self.mock_supabase = MagicMock()
        self.inventory_service = InventoryService(self.mock_supabase)
        self.today = date.today().isoformat()
        self.future_date = (date.today() + timedelta(days=10)).isoformat()

    def test_decrement_stock_success(self):
        self.mock_supabase.table().select().eq().eq().gte().order().is_().execute.return_value = MagicMock(
            data=[
                {
                    "id": "batch-1",
                    "quantity": 10,
                    "quantity_sold": 0,
                }
            ]
        )
        
        self.mock_supabase.table().update().eq().eq().execute.return_value = MagicMock(
            data=[{"id": "batch-1", "quantity_sold": 5}]
        )
        
        result = self.inventory_service.decrement_stock("prod-1", 5)
        assert len(result) == 1
        assert result[0]["batch_id"] == "batch-1"
        assert result[0]["quantity_decremented"] == 5

    def test_decrement_stock_insufficient(self):
        self.mock_supabase.table().select().eq().eq().gte().order().is_().execute.return_value = MagicMock(
            data=[
                {
                    "id": "batch-1",
                    "quantity": 10,
                    "quantity_sold": 8,
                }
            ]
        )
        
        with pytest.raises(InsufficientStockError) as exc:
            self.inventory_service.decrement_stock("prod-1", 5)
        assert exc.value.available == 2

    def test_decrement_stock_conflict_retry_failure(self):
        self.mock_supabase.table().select().eq().eq().gte().order().is_().execute.return_value = MagicMock(
            data=[
                {
                    "id": "batch-1",
                    "quantity": 10,
                    "quantity_sold": 0,
                }
            ]
        )
        
        # Simulate optimistic lock failure always
        self.mock_supabase.table().update().eq().eq().execute.return_value = MagicMock(
            data=[]
        )
        
        with pytest.raises(InventoryServiceError) as exc:
            self.inventory_service.decrement_stock("prod-1", 5, max_retries=2)
        assert "Hệ thống đang bận" in exc.value.message
