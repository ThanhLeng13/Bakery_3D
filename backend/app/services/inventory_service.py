"""Inventory service — quản lý lô hàng bánh ngọt.

Chức năng:
- Baker thêm / sửa / ẩn lô hàng (product_batches)
- Public: xem tổng stock còn lại của một sản phẩm
- Decrement stock theo FIFO (lô gần hết hạn nhất trước)
"""

from datetime import date, datetime
from typing import Any


class InventoryServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class InsufficientStockError(InventoryServiceError):
    def __init__(self, available: int, requested: int):
        super().__init__(
            f"Không đủ hàng. Còn {available} cái, yêu cầu {requested} cái.",
            status_code=409,
        )
        self.available = available
        self.requested = requested


class BatchNotFoundError(InventoryServiceError):
    def __init__(self):
        super().__init__("Không tìm thấy lô hàng.", status_code=404)


class InventoryService:
    """Service quản lý lô hàng bánh ngọt."""

    def __init__(self, supabase_client: Any):
        self._db = supabase_client

    # ─── Public ────────────────────────────────────────────────────────────────

    async def get_product_stock(self, product_id: str) -> dict:
        """
        Tổng hợp stock khả dụng của một sản phẩm.

        Chỉ tính các lô:
        - is_active = true
        - expires_at >= today (còn hạn)
        - quantity_sold < quantity (còn hàng)

        Returns:
            {
                total_available: int,
                expires_soonest: str | None,   # ngày hết hạn gần nhất (YYYY-MM-DD)
                batches: [{ id, quantity_available, expires_at, produced_at }]
            }
        """
        today = date.today().isoformat()

        result = (
            self._db.table("product_batches")
            .select("id, quantity, quantity_sold, produced_at, expires_at")
            .eq("product_id", product_id)
            .eq("is_active", True)
            .gte("expires_at", today)
            .order("expires_at", desc=False)
            .execute()
        )

        batches = result.data or []

        available_batches = []
        total = 0
        for b in batches:
            avail = b["quantity"] - b["quantity_sold"]
            if avail > 0:
                total += avail
                available_batches.append(
                    {
                        "id": b["id"],
                        "quantity_available": avail,
                        "produced_at": b["produced_at"],
                        "expires_at": b["expires_at"],
                    }
                )

        expires_soonest = available_batches[0]["expires_at"] if available_batches else None

        return {
            "product_id": product_id,
            "total_available": total,
            "expires_soonest": expires_soonest,
            "batches": available_batches,
        }

    async def get_stock_by_branch(self, product_id: str) -> dict:
        """
        Tồn kho theo từng chi nhánh của một sản phẩm.
        Luôn trả về TẤT CẢ chi nhánh (kể cả hết hàng),
        để khách biết chi nhánh nào còn/hết hàng.

        Returns:
            {
                product_id: str,
                total_available: int,
                branches: [
                    {
                        branch_id: str | None,
                        branch_name: str,
                        branch_address: str | None,
                        quantity_available: int,
                        expires_soonest: str | None,
                    }
                ]
            }
        """
        today = date.today().isoformat()

        # 1. Fetch ALL branches (no is_active filter — branches table doesn't have this column)
        all_branches_result = (
            self._db.table("branches")
            .select("id, name, address")
            .order("name", desc=False)
            .execute()
        )
        all_branches = all_branches_result.data or []

        # Build branch_map starting with all branches at 0 stock
        branch_map: dict[str | None, dict] = {
            b["id"]: {
                "branch_id": b["id"],
                "branch_name": b["name"],
                "branch_address": b.get("address"),
                "quantity_available": 0,
                "expires_soonest": None,
            }
            for b in all_branches
        }

        # 2. Fetch batches (active, not expired) with branch info
        result = (
            self._db.table("product_batches")
            .select(
                "id, quantity, quantity_sold, expires_at, branch_id, "
                "branches(id, name, address)"
            )
            .eq("product_id", product_id)
            .eq("is_active", True)
            .gte("expires_at", today)
            .order("expires_at", desc=False)
            .execute()
        )

        batches = result.data or []

        # 3. Accumulate available stock per branch (including branch_id=None = "Kho chung")
        for b in batches:
            avail = b["quantity"] - b["quantity_sold"]
            branch_id = b.get("branch_id")
            branch_data = b.get("branches")

            # Resolve branch name for null/unknown branches
            if branch_id is None:
                key = None
                if key not in branch_map:
                    branch_map[key] = {
                        "branch_id": None,
                        "branch_name": "Kho chung (chưa phân chi nhánh)",
                        "branch_address": None,
                        "quantity_available": 0,
                        "expires_soonest": None,
                    }
            else:
                key = branch_id
                if key not in branch_map:
                    # Branch exists in batch but not in branches table (shouldn't happen)
                    if branch_data and isinstance(branch_data, dict):
                        bname = branch_data.get("name", "Chi nhánh")
                        baddress = branch_data.get("address")
                    elif branch_data and isinstance(branch_data, list) and branch_data:
                        bname = branch_data[0].get("name", "Chi nhánh")
                        baddress = branch_data[0].get("address")
                    else:
                        bname = "Chi nhánh"
                        baddress = None
                    branch_map[key] = {
                        "branch_id": branch_id,
                        "branch_name": bname,
                        "branch_address": baddress,
                        "quantity_available": 0,
                        "expires_soonest": None,
                    }

            if avail > 0:
                entry = branch_map[key]
                entry["quantity_available"] += avail
                if entry["expires_soonest"] is None:
                    entry["expires_soonest"] = b["expires_at"]

        # 4. Sort: branches with stock first, then out-of-stock
        branches = sorted(
            branch_map.values(),
            key=lambda x: (x["quantity_available"] == 0, x["branch_name"]),
        )
        total = sum(b["quantity_available"] for b in branches)

        return {
            "product_id": product_id,
            "total_available": total,
            "branches": branches,
        }


    # ─── Baker ─────────────────────────────────────────────────────────────────

    async def add_batch(
        self,
        product_id: str,
        quantity: int,
        produced_at: str,
        expires_at: str,
        notes: str | None,
        branch_id: str | None,
        baker: dict,
    ) -> dict:
        """Bếp thêm lô bánh mới."""
        if quantity <= 0:
            raise InventoryServiceError("Số lượng phải lớn hơn 0.")
        if expires_at <= produced_at:
            raise InventoryServiceError("Ngày hết hạn phải sau ngày sản xuất.")

        # Verify product exists and is sweet type
        product = (
            self._db.table("products")
            .select("id, name, product_type")
            .eq("id", product_id)
            .eq("is_active", True)
            .maybe_single()
            .execute()
        )
        if not product or not product.data:
            raise InventoryServiceError("Không tìm thấy sản phẩm.", status_code=404)
        if product.data.get("product_type") != "sweet":
            raise InventoryServiceError(
                "Chỉ bánh ngọt mới có thể thêm lô hàng. Bánh kem làm theo đơn.",
                status_code=400,
            )

        data = {
            "product_id": product_id,
            "quantity": quantity,
            "quantity_sold": 0,
            "produced_at": produced_at,
            "expires_at": expires_at,
            "notes": notes,
            "branch_id": branch_id,
            "created_by": baker["id"],
            "is_active": True,
        }

        result = self._db.table("product_batches").insert(data).execute()
        if not result.data:
            raise InventoryServiceError("Không thể thêm lô hàng.", status_code=500)

        return result.data[0]

    async def get_batches(self, product_id: str | None = None, branch_id: str | None = None) -> list[dict]:
        """Liệt kê tất cả lô (baker dashboard). Có thể lọc theo product_id và branch_id."""
        query = (
            self._db.table("product_batches")
            .select(
                "id, product_id, quantity, quantity_sold, produced_at, expires_at, "
                "notes, is_active, created_at, branch_id, "
                "products(name, category), "
                "branches(id, name)"
            )
            .order("expires_at", desc=False)
        )
        if product_id:
            query = query.eq("product_id", product_id)
        if branch_id:
            query = query.eq("branch_id", branch_id)

        result = query.execute()
        rows = result.data or []

        # Enrich with quantity_available
        for r in rows:
            r["quantity_available"] = r["quantity"] - r["quantity_sold"]
            today = date.today().isoformat()
            r["is_expired"] = r["expires_at"] < today

        return rows

    async def update_batch(self, batch_id: str, updates: dict, baker: dict) -> dict:
        """
        Baker cập nhật lô: có thể đổi quantity, notes, is_active.
        Không cho phép giảm quantity xuống dưới quantity_sold.
        """
        # Fetch current batch
        current = (
            self._db.table("product_batches")
            .select("*")
            .eq("id", batch_id)
            .maybe_single()
            .execute()
        )
        if not current or not current.data:
            raise BatchNotFoundError()

        batch = current.data

        allowed_fields = {"quantity", "notes", "is_active", "expires_at"}
        patch = {k: v for k, v in updates.items() if k in allowed_fields}

        # Validate new quantity >= quantity_sold
        new_qty = patch.get("quantity", batch["quantity"])
        if new_qty < batch["quantity_sold"]:
            raise InventoryServiceError(
                f"Không thể giảm số lượng xuống {new_qty}: "
                f"đã bán {batch['quantity_sold']} cái.",
                status_code=400,
            )

        patch["updated_at"] = "now()"

        result = (
            self._db.table("product_batches")
            .update(patch)
            .eq("id", batch_id)
            .execute()
        )
        if not result.data:
            raise InventoryServiceError("Không thể cập nhật lô hàng.", status_code=500)

        updated = result.data[0]
        updated["quantity_available"] = updated["quantity"] - updated["quantity_sold"]
        return updated

    # ─── Purchase ──────────────────────────────────────────────────────────────

    async def decrement_stock(
        self,
        product_id: str,
        quantity_needed: int,
        branch_id: str | None = None,
    ) -> list[dict]:
        """
        Trừ stock theo FIFO (lô gần hết hạn nhất trước).
        Nếu branch_id được cung cấp, chỉ trừ từ lô của chi nhánh đó.

        Returns:
            List of { batch_id, quantity_decremented }
        """
        today = date.today().isoformat()

        query = (
            self._db.table("product_batches")
            .select("id, quantity, quantity_sold")
            .eq("product_id", product_id)
            .eq("is_active", True)
            .gte("expires_at", today)
            .order("expires_at", desc=False)
        )

        if branch_id is not None:
            query = query.eq("branch_id", branch_id)

        result = query.execute()

        batches = result.data or []
        total_available = sum(b["quantity"] - b["quantity_sold"] for b in batches)

        if total_available < quantity_needed:
            raise InsufficientStockError(total_available, quantity_needed)

        decrements = []
        remaining = quantity_needed

        for batch in batches:
            if remaining <= 0:
                break
            avail = batch["quantity"] - batch["quantity_sold"]
            if avail <= 0:
                continue

            take = min(avail, remaining)
            new_sold = batch["quantity_sold"] + take

            self._db.table("product_batches").update(
                {"quantity_sold": new_sold, "updated_at": datetime.now().isoformat()}
            ).eq("id", batch["id"]).execute()

            decrements.append({"batch_id": batch["id"], "quantity_decremented": take})
            remaining -= take

        return decrements
