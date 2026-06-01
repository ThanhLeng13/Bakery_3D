"""Branches API endpoints.

Public endpoint:
    GET /api/v1/branches  — Lấy danh sách chi nhánh
"""

from fastapi import APIRouter, HTTPException

from app.core.config import settings

router = APIRouter()


def _get_service_client():
    from supabase import create_client
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


@router.get("")
async def list_branches():
    """Lấy danh sách chi nhánh đang hoạt động (Public)."""
    client = _get_service_client()
    try:
        result = (
            client.table("branches")
            .select("id, name, address, phone")
            .eq("is_active", True)
            .order("name", desc=False)
            .execute()
        )
        return {"branches": result.data or []}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Không thể tải danh sách chi nhánh.")
