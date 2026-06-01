"""Purchases API endpoint — mua bánh ngọt trực tiếp.

POST /api/v1/purchases
    Yêu cầu đăng nhập (khách hàng).
    Trừ stock ngay, lưu lịch sử purchases + purchase_items.
    Thanh toán offline (đến quán trả tiền).
"""

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
    branch_id: str | None = Field(default=None, description="UUID chi nhánh mua hàng")


# ─── Route ─────────────────────────────────────────────────────────────────────

@router.post("", status_code=201)
async def create_purchase(
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

    # 3. Check stock availability for all items (branch-aware)
    stock_checks = []
    for item in body.items:
        if body.branch_id:
            # Check stock for the SPECIFIC branch
            branch_stock = await inv_svc.get_stock_by_branch(item.product_id)
            branch = next(
                (b for b in branch_stock["branches"] if b["branch_id"] == body.branch_id),
                None,
            )
            available = branch["quantity_available"] if branch else 0
        else:
            # No branch specified — check global stock
            stock = await inv_svc.get_product_stock(item.product_id)
            available = stock["total_available"]

        if available < item.quantity:
            pname = products_map[item.product_id]["name"]
            raise HTTPException(
                status_code=409,
                detail=(
                    f"'{pname}': Còn {available} cái, "
                    f"yêu cầu {item.quantity} cái."
                ),
            )
        stock_checks.append(available)


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
        "status": "completed",
        "notes": body.notes,
        "branch_id": body.branch_id,
    }
    purchase_result = db.table("purchases").insert(purchase_data).execute()
    if not purchase_result.data:
        raise HTTPException(status_code=500, detail="Không thể tạo đơn mua hàng.")

    purchase = purchase_result.data[0]
    purchase_id = purchase["id"]

    # 6. Decrement stock FIFO + create purchase_items
    purchase_items = []
    try:
        for item in body.items:
            product = products_map[item.product_id]
            decrements = await inv_svc.decrement_stock(
                item.product_id,
                item.quantity,
                branch_id=body.branch_id,
            )

            # Create one purchase_item per batch decremented
            for dec in decrements:
                pi_data = {
                    "purchase_id": purchase_id,
                    "product_id": item.product_id,
                    "batch_id": dec["batch_id"],
                    "quantity": dec["quantity_decremented"],
                    "unit_price": int(product["base_price"]),
                }
                pi_result = db.table("purchase_items").insert(pi_data).execute()
                if pi_result.data:
                    pi = pi_result.data[0]
                    pi["product_name"] = product["name"]
                    purchase_items.append(pi)

    except (InsufficientStockError, InventoryServiceError) as e:
        # Rollback: cancel the purchase record
        db.table("purchases").update({"status": "cancelled"}).eq(
            "id", purchase_id
        ).execute()
        raise HTTPException(status_code=409, detail=e.message)
    except Exception:
        db.table("purchases").update({"status": "cancelled"}).eq(
            "id", purchase_id
        ).execute()
        raise HTTPException(status_code=500, detail="Lỗi xử lý mua hàng.")

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
async def get_purchase_history(
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
