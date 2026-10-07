"""Manager endpoints for assigning operational user roles."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from app.core.dependencies import get_supabase_client, require_admin

router = APIRouter()
ASSIGNABLE_ROLES = {"customer", "staff", "baker"}


class UpdateUserRoleRequest(BaseModel):
    role: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        if value not in ASSIGNABLE_ROLES:
            raise ValueError("Role must be customer, staff, or baker")
        return value


@router.get("")
def list_users(admin: dict = Depends(require_admin)):
    """List accounts so a manager can assign staff and baker roles."""
    db = get_supabase_client(use_service_role=True)
    try:
        result = (
            db.table("users")
            .select("id, email, full_name, phone, role, branch_id")
            .order("full_name", desc=False)
            .execute()
        )
        users = result.data or []
        return {"users": users, "total": len(users)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Không thể tải danh sách tài khoản.") from exc


@router.patch("/{user_id}/role")
def update_user_role(
    user_id: str,
    body: UpdateUserRoleRequest,
    admin: dict = Depends(require_admin),
):
    """Assign a non-manager role while preventing accidental self-demotion."""
    if user_id == admin["id"]:
        raise HTTPException(status_code=400, detail="Không thể tự thay đổi quyền quản lý.")

    db = get_supabase_client(use_service_role=True)
    existing = db.table("users").select("id, role").eq("id", user_id).maybe_single().execute()
    if not existing or not existing.data:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")
    if existing.data.get("role") == "admin":
        raise HTTPException(status_code=403, detail="Không thể thay đổi tài khoản quản lý khác.")

    result = db.table("users").update({"role": body.role}).eq("id", user_id).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Không thể cập nhật vai trò.")
    return result.data[0]
