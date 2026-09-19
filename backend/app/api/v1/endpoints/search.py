"""CLIP image search endpoint — trụ cột 2 của đề tài.

Endpoints:
- POST /api/v1/search/by-image  — tải ảnh lên, tìm sản phẩm gần giống nhất
- GET  /api/v1/search/status    — trạng thái model (dùng cho health check)
"""

import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.services.clip_service import (
    ClipSearchService,
    ClipServiceError,
    get_model_status,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/status")
def search_status():
    """Cho biết model CLIP đã sẵn sàng chưa và đã có bao nhiêu embedding.

    Endpoint này KHÔNG kích hoạt load model — chỉ báo cáo trạng thái hiện tại,
    để health check không tốn 45 giây tải model.
    """
    from app.core.dependencies import get_supabase_client

    status = get_model_status()

    embedding_count = 0
    try:
        client = get_supabase_client(use_service_role=True)
        response = (
            client.table("cake_embeddings").select("id", count="exact").execute()
        )
        embedding_count = response.count or 0
    except Exception:
        # Bảng chưa tồn tại (migration chưa chạy) → coi như 0, không làm sập health check.
        logger.warning("Could not count cake_embeddings", exc_info=True)

    return {
        **status,
        "embedding_count": embedding_count,
        "ready": status["available"] and embedding_count > 0,
    }


@router.post("/by-image")
async def search_by_image(
    file: UploadFile = File(..., description="Ảnh bánh khách tải lên"),
    match_count: int = Form(default=6, ge=1, le=20, description="Số kết quả trả về"),
    match_threshold: float = Form(
        default=0.0, ge=0.0, le=1.0, description="Ngưỡng tương đồng tối thiểu"
    ),
):
    """Tìm sản phẩm trong kho gần giống nhất với ảnh khách tải lên.

    Quy trình:
        1. Đọc bytes ảnh, kiểm tra hợp lệ (định dạng, kích thước, dung lượng)
        2. Sinh vector 512 chiều bằng CLIP ViT-B-32
        3. So sánh cosine với toàn bộ embedding trong kho qua RPC match_cakes
        4. Trả về top-K kèm % tương đồng

    Lỗi trả về:
        400 - ảnh không hợp lệ hoặc quá nhỏ
        413 - ảnh vượt quá 10 MB
        503 - model chưa sẵn sàng hoặc không truy vấn được kho
    """
    raw = await file.read()

    service = ClipSearchService()
    try:
        return service.search_by_image(
            raw,
            match_count=match_count,
            match_threshold=match_threshold,
        )
    except ClipServiceError as exc:
        # exc.message là thông báo đã được viết cho người dùng; chi tiết kỹ thuật
        # chỉ nằm trong log (xem clip_service), không lộ ra response.
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
