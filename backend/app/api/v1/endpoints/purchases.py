"""Purchases API endpoint — mua bánh ngọt trực tiếp.

POST /api/v1/purchases
    Yêu cầu đăng nhập (khách hàng).
    Trừ stock ngay, lưu lịch sử purchases + purchase_items.
    Thanh toán offline (đến quán trả tiền).
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.services.inventory_service import (
    InsufficientStockError,
    InventoryService,
    InventoryServiceError,
)

router = APIRouter()


# ─── Dependency ────────────────────────────────────────────────────────────────

def _get_db():
    """Tao Supabase client voi service role key moi request."""
    from supabase import create_client
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


# ─── Schemas ───────────────────────────────────────────────────────────────────

class PurchaseItem(BaseModel):
    product_id: str = Field(..., description="UUID sản phẩm bánh ngọt")
    quantity: int = Field(..., ge=1, le=99, description="Số lượng mua")


class CreatePurchaseRequest(BaseModel):
    items: list[PurchaseItem] = Field(..., min_length=1, description="Danh sách sản phẩm mua")
    customer_name: str = Field(..., min_length=1, max_length=100)
    customer_phone: str = Field(..., pattern=r"^\d{10}$", description="10 chữ số")
    notes: str | None = Field(default=None, max_length=300)
    branch_id: str = Field(..., description="UUID chi nhánh mua hàng (bắt buộc)")


# ─── Helpers ───────────────────────────────────────────────────────────────────

import logging as _logging
_logger = _logging.getLogger(__name__)

def _rollback_purchase(
    inv_svc: InventoryService,
    db,
    decrements: list[dict],
    purchase_id: str,
) -> None:
    """
    Thực hiện rollback từng bước độc lập. Mỗi bước được bọc trong try/except
    riêng để đảm bảo:
    - Tất cả các bước đều được thực hiện dù bước trước có lỗi
    - Exception gốc (409/500) không bị che khuất bởi lỗi rollback
    """
    # Step 1: Restore stock
    try:
        inv_svc._rollback_decrements(decrements)
    except Exception as rollback_err:
        _logger.error(
            "Rollback step 1 (restore stock) failed for purchase %s: %s",
            purchase_id, rollback_err,
        )

    # Step 2: Delete orphaned purchase_items
    try:
        db.table("purchase_items").delete().eq("purchase_id", purchase_id).execute()
    except Exception as rollback_err:
        _logger.error(
            "Rollback step 2 (delete purchase_items) failed for purchase %s: %s",
            purchase_id, rollback_err,
        )

    # Step 3: Mark purchase as cancelled
    try:
        db.table("purchases").update({"status": "cancelled"}).eq(
            "id", purchase_id
        ).execute()
    except Exception as rollback_err:
        _logger.error(
            "Rollback step 3 (cancel purchase) failed for purchase %s: %s",
            purchase_id, rollback_err,
        )


# ─── Route ─────────────────────────────────────────────────────────────────────

@router.post("", status_code=201)
def create_purchase(
    body: CreatePurchaseRequest,
    customer: dict = Depends(get_current_user),
):
    """
    Mua bánh ngọt — trừ stock ngay và lưu lịch sử.

    Luồng:
    1. Validate từng sản phẩm là bánh ngọt (product_type = 'sweet')
    2. Tính giá từ base_price (hoặc giá lô nếu có)
    3. Kiểm tra stock đủ cho tất cả items
    4. Tạo purchase record
    5. Decrement stock FIFO từng sản phẩm
    6. Tạo purchase_items
    7. Return receipt

    Thanh toán: offline (khách đến quán trả tiền mặt).
    """
    db = _get_db()
    inv_svc = InventoryService(db)

    # 1. Fetch all products in one query
    product_ids = [item.product_id for item in body.items]
    products_result = (
        db.table("products")
        .select("id, name, base_price, product_type, is_active")
        .in_("id", product_ids)
        .execute()
    )
    products_map = {p["id"]: p for p in (products_result.data or [])}

    # 2. Validate products
    for item in body.items:
        product = products_map.get(item.product_id)
        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Không tìm thấy sản phẩm: {item.product_id}",
            )
        if not product.get("is_active"):
            raise HTTPException(
                status_code=400,
                detail=f"Sản phẩm '{product['name']}' hiện không bán.",
            )
        if product.get("product_type") != "sweet":
            raise HTTPException(
                status_code=400,
                detail=(
                    f"'{product['name']}' là bánh kem — vui lòng dùng tính năng Đặt hàng, "
                    "không thể thêm vào giỏ bánh ngọt."
                ),
            )

    # 2b. Validate branch_id tồn tại và đang hoạt động
    # Kiểm tra trước khi insert để tránh lỗi foreign key violation 500 không rõ ràng.
    branch_check = (
        db.table("branches")
        .select("id, name, is_active")
        .eq("id", body.branch_id)
        .maybe_single()
        .execute()
    )
    if not branch_check or not branch_check.data:
        raise HTTPException(
            status_code=404,
            detail=f"Không tìm thấy chi nhánh: {body.branch_id}",
        )
    if not branch_check.data.get("is_active"):
        raise HTTPException(
            status_code=400,
            detail=f"Chi nhánh '{branch_check.data['name']}' hiện không hoạt động.",
        )

    # 3. Check stock at the selected branch in a SINGLE query
    # Previously called get_stock_by_branch(product_id) N times (2N DB roundtrips).
    # Now: one product_batches query for all product_ids at the specific branch → O(1) queries.
    aggregated: dict[str, int] = {}
    for item in body.items:
        aggregated[item.product_id] = aggregated.get(item.product_id, 0) + item.quantity

    today = date.today().isoformat()
    batch_result = (
        db.table("product_batches")
        .select("product_id, quantity, quantity_sold")
        .in_("product_id", list(aggregated.keys()))
        .eq("branch_id", body.branch_id)
        .eq("is_active", True)
        .gte("expires_at", today)
        .execute()
    )
    # Aggregate available stock per product_id in memory
    stock_at_branch: dict[str, int] = {}
    for row in (batch_result.data or []):
        pid = row["product_id"]
        avail = max(0, row["quantity"] - row["quantity_sold"])
        stock_at_branch[pid] = stock_at_branch.get(pid, 0) + avail

    for product_id, total_qty in aggregated.items():
        available = stock_at_branch.get(product_id, 0)
        if available < total_qty:
            pname = products_map[product_id]["name"]
            raise HTTPException(
                status_code=409,
                detail=(
                    f"'{pname}': Chi nhánh chọn còn {available} cái, "
                    f"yêu cầu {total_qty} cái."
                ),
            )


    # 4. Calculate total price
    total_price = sum(
        products_map[item.product_id]["base_price"] * item.quantity
        for item in body.items
    )

    # 5. Create purchase record
    purchase_data = {
        "customer_id": customer["id"],
        "customer_name": body.customer_name,
        "customer_phone": body.customer_phone,
        "total_price": int(total_price),
        "status": "pending",
        "notes": body.notes,
        "branch_id": body.branch_id,
    }
    purchase_result = db.table("purchases").insert(purchase_data).execute()
    if not purchase_result.data:
        raise HTTPException(status_code=500, detail="Không thể tạo đơn mua hàng.")

    purchase = purchase_result.data[0]
    purchase_id = purchase["id"]

    # 6. Decrement stock FIFO + create purchase_items
    # Dùng aggregated.items() thay vì body.items để tránh gọi decrement_stock nhiều lần
    # cho cùng một product_id (trường hợp duplicate trong request).
    pending_items: list[dict] = []   # collected for bulk insert after all decrements
    all_decrements: list[dict] = []  # track ALL decrements for rollback on partial failure
    try:
        for product_id, total_qty in aggregated.items():
            product = products_map[product_id]
            decrements = inv_svc.decrement_stock(
                product_id,
                total_qty,
                branch_id=body.branch_id,
            )
            all_decrements.extend(decrements)

            # Collect purchase_item rows — one row per batch decremented
            for dec in decrements:
                pending_items.append({
                    "purchase_id": purchase_id,
                    "product_id": product_id,
                    "batch_id": dec["batch_id"],
                    "quantity": dec["quantity_decremented"],
                    "unit_price": int(product["base_price"]),
                })

        # Bulk insert all purchase_items in a single roundtrip
        if pending_items:
            db.table("purchase_items").insert(pending_items).execute()

        # Update purchase status to "completed" only after successfully decrementing stock and inserting all items
        db.table("purchases").update({"status": "completed"}).eq("id", purchase_id).execute()

    except (InsufficientStockError, InventoryServiceError) as e:
        _rollback_purchase(inv_svc, db, all_decrements, purchase_id)
        raise HTTPException(status_code=409, detail=e.message) from e
    except Exception as e:
        _logger.exception("Lỗi không mong muốn trong luồng xử lý mua hàng (purchase_id=%s): %s", purchase_id, e)
        _rollback_purchase(inv_svc, db, all_decrements, purchase_id)
        raise HTTPException(status_code=500, detail="Lỗi xử lý mua hàng.") from e


    # 7. Build receipt
    receipt_items = []
    for item in body.items:
        product = products_map[item.product_id]
        receipt_items.append(
            {
                "product_id": item.product_id,
                "product_name": product["name"],
                "quantity": item.quantity,
                "unit_price": int(product["base_price"]),
                "subtotal": int(product["base_price"]) * item.quantity,
            }
        )

    return {
        "purchase_id": purchase_id,
        "customer_name": body.customer_name,
        "customer_phone": body.customer_phone,
        "items": receipt_items,
        "total_price": int(total_price),
        "status": "completed",
        "message": "Mua hàng thành công! Vui lòng đến quán thanh toán và nhận bánh.",
        "created_at": purchase["created_at"],
    }


@router.get("/history")
def get_purchase_history(
    customer: dict = Depends(get_current_user),
):
    """Lịch sử mua bánh ngọt của khách hàng hiện tại."""
    db = _get_db()

    result = (
        db.table("purchases")
        .select(
            "id, total_price, status, notes, created_at, "
            "purchase_items(id, quantity, unit_price, product_id, "
            "products(name, category))"
        )
        .eq("customer_id", customer["id"])
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )

    return {"purchases": result.data or [], "total": len(result.data or [])}
