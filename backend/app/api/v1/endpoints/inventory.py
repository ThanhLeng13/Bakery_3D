"""Inventory API endpoints.

Baker endpoints (require_baker):
    POST   /api/v1/baker/batches              — Thêm lô mới
    GET    /api/v1/baker/batches              — Liệt kê lô (tất cả hoặc theo sản phẩm)
    PATCH  /api/v1/baker/batches/{batch_id}   — Cập nhật lô

Public endpoints:
    GET    /api/v1/products/{product_id}/stock — Stock còn lại của sản phẩm
"""

from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.dependencies import require_baker, get_supabase_client
from app.services.inventory_service import (
    BatchNotFoundError,
    InsufficientStockError,
    InventoryService,
    InventoryServiceError,
)

baker_router = APIRouter()
public_router = APIRouter()


# ─── Dependency ────────────────────────────────────────────────────────────────

def _get_inventory_service() -> InventoryService:
    # Uses threading.local()-cached client from get_supabase_client()
    client = get_supabase_client(use_service_role=True)
    return InventoryService(client)


# ─── Schemas ───────────────────────────────────────────────────────────────────

class AddBatchRequest(BaseModel):
    product_id: str = Field(..., description="UUID sản phẩm (phải là bánh ngọt)")
    quantity: int = Field(..., ge=1, le=9999, description="Số lượng lô")
    produced_at: date = Field(..., description="Ngày sản xuất (YYYY-MM-DD)")
    expires_at: date = Field(..., description="Ngày hết hạn (YYYY-MM-DD)")
    notes: str | None = Field(default=None, max_length=300, description="Ghi chú bếp")
    branch_id: str | None = Field(default=None, description="UUID chi nhánh (tùy chọn)")


class UpdateBatchRequest(BaseModel):
    quantity: int | None = Field(default=None, ge=1, le=9999)
    notes: str | None = Field(default=None, max_length=300)
    is_active: bool | None = Field(default=None)
    expires_at: str | None = Field(default=None)


class BulkAddBatchRequest(BaseModel):
    """Create batches for multiple branches in a single atomic request."""
    product_id: str = Field(..., description="UUID sản phẩm (phải là bánh ngọt)")
    quantity: int = Field(..., ge=1, le=9999, description="Số lượng mỗi lô")
    produced_at: date = Field(..., description="Ngày sản xuất (YYYY-MM-DD)")
    expires_at: date = Field(..., description="Ngày hết hạn (YYYY-MM-DD)")
    notes: str | None = Field(default=None, max_length=300, description="Ghi chú bếp")
    branch_ids: list[str] = Field(..., min_length=1, description="Danh sách UUID chi nhánh")


# ─── Baker Routes ──────────────────────────────────────────────────────────────

@baker_router.post("/batches", status_code=201)
def add_batch(
    body: AddBatchRequest,
    baker: dict = Depends(require_baker),
):
    """Thêm lô bánh ngọt mới (Baker only)."""
    svc = _get_inventory_service()
    try:
        result = svc.add_batch(
            product_id=body.product_id,
            quantity=body.quantity,
            produced_at=body.produced_at.isoformat(),
            expires_at=body.expires_at.isoformat(),
            notes=body.notes,
            branch_id=body.branch_id,
            baker=baker,
        )
        return result
    except InventoryServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@baker_router.post("/batches/bulk", status_code=201)
def add_batch_bulk(
    body: BulkAddBatchRequest,
    baker: dict = Depends(require_baker),
):
    """Tạo lô bánh ngọt cho nhiều chi nhánh trong một request.

    NOT truly atomic — each branch insert is a separate DB operation.
    On partial failure, returns 207 Multi-Status with details of which
    branches succeeded and which failed, so the frontend can retry
    only the failed ones (avoiding duplicates).

    Returns:
        201: All branches succeeded.
        207: Partial success — some branches failed. Response includes
             succeeded_branch_ids and failed details for retry.
    """
    from fastapi.responses import JSONResponse

    svc = _get_inventory_service()
    results = []
    errors = []
    succeeded_branch_ids = []

    for branch_id in body.branch_ids:
        try:
            result = svc.add_batch(
                product_id=body.product_id,
                quantity=body.quantity,
                produced_at=body.produced_at.isoformat(),
                expires_at=body.expires_at.isoformat(),
                notes=body.notes,
                branch_id=branch_id,
                baker=baker,
            )
            results.append(result)
            succeeded_branch_ids.append(branch_id)
        except InventoryServiceError as e:
            errors.append({"branch_id": branch_id, "error": e.message})

    if errors:
        # 207 Multi-Status: some succeeded, some failed
        # Frontend should retry only the failed branch_ids
        return JSONResponse(
            status_code=207,
            content={
                "message": f"Thành công {len(results)}/{len(body.branch_ids)} chi nhánh",
                "batches": results,
                "succeeded_branch_ids": succeeded_branch_ids,
                "errors": errors,
            },
        )

    return {"batches": results, "total": len(results)}


@baker_router.get("/batches")
def list_batches(
    product_id: str | None = Query(default=None, description="Lọc theo sản phẩm"),
    branch_id: str | None = Query(default=None, description="Lọc theo chi nhánh"),
    baker: dict = Depends(require_baker),
):
    """Liệt kê lô hàng bánh ngọt (Baker only). Lọc tùy chọn theo product_id và branch_id."""
    svc = _get_inventory_service()
    try:
        batches = svc.get_batches(product_id=product_id, branch_id=branch_id)
        return {"batches": batches, "total": len(batches)}
    except InventoryServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@baker_router.patch("/batches/{batch_id}")
def update_batch(
    batch_id: str,
    body: UpdateBatchRequest,
    baker: dict = Depends(require_baker),
):
    """Cập nhật lô hàng (Baker only). Có thể đổi số lượng, ghi chú, ẩn/hiện."""
    svc = _get_inventory_service()
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="Không có trường nào được cập nhật.")
    try:
        result = svc.update_batch(batch_id=batch_id, updates=updates, baker=baker)
        return result
    except BatchNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e
    except InventoryServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


# ─── Public Routes ─────────────────────────────────────────────────────────────

@public_router.get("/products/{product_id}/stock")
def get_product_stock(product_id: str):
    """
    Xem stock khả dụng của sản phẩm bánh ngọt (Public).

    Returns:
        total_available: tổng số còn lại
        expires_soonest: ngày hết hạn gần nhất (YYYY-MM-DD)
        batches: danh sách lô còn hàng
    """
    svc = _get_inventory_service()
    try:
        return svc.get_product_stock(product_id=product_id)
    except InventoryServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@public_router.get("/products/{product_id}/stock-by-branch")
def get_stock_by_branch(product_id: str):
    """
    Xem tồn kho theo từng chi nhánh của sản phẩm bánh ngọt (Public).

    Returns:
        product_id: str
        total_available: tổng số còn lại toàn hệ thống
        branches: [{ branch_id, branch_name, branch_address, quantity_available, expires_soonest }]
    """
    svc = _get_inventory_service()
    try:
        return svc.get_stock_by_branch(product_id=product_id)
    except InventoryServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
