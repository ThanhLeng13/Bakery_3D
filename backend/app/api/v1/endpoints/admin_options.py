"""Admin cake options management API endpoints.

Endpoints:
- GET    /api/v1/admin/options              - List all options (filter by type)
- POST   /api/v1/admin/options              - Create new option
- PUT    /api/v1/admin/options/{id}         - Update option
- DELETE /api/v1/admin/options/{id}         - Delete option
- PATCH  /api/v1/admin/options/{id}/status  - Toggle active/inactive

All endpoints require Admin role authentication.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.dependencies import require_admin, get_supabase_client

router = APIRouter()

VALID_OPTION_TYPES = {"size", "flavor", "topping", "color"}


class CreateOptionRequest(BaseModel):
    """Request body for creating a cake option."""

    type: str = Field(..., description="Option type: size, flavor, topping, or color")
    name: str = Field(..., min_length=1, max_length=100, description="Unique identifier name")
    label: str = Field(..., min_length=1, max_length=200, description="Display label (Vietnamese)")
    price_modifier: int = Field(default=0, ge=0, description="Additional price in VND")
    sort_order: int = Field(default=0, ge=0, description="Display order")
    icon: Optional[str] = Field(default=None, max_length=10, description="Emoji icon")
    hex_color: Optional[str] = Field(default=None, max_length=20, description="Hex color code")
    is_active: bool = Field(default=True)


class UpdateOptionRequest(BaseModel):
    """Request body for updating a cake option."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    label: Optional[str] = Field(default=None, min_length=1, max_length=200)
    price_modifier: Optional[int] = Field(default=None, ge=0)
    sort_order: Optional[int] = Field(default=None, ge=0)
    icon: Optional[str] = Field(default=None, max_length=10)
    hex_color: Optional[str] = Field(default=None, max_length=20)
    is_active: Optional[bool] = None


class ToggleStatusRequest(BaseModel):
    """Request body for toggling option status."""

    is_active: bool


@router.get("")
def list_options(
    type: Optional[str] = Query(default=None, description="Filter by type: size, flavor, topping, color"),
    is_active: Optional[bool] = Query(default=None, description="Filter by active status"),
    current_user: dict = Depends(require_admin),
):
    """
    List all cake options with optional filters.

    Returns all options including inactive ones (admin view).
    Requires Admin role.
    """
    supabase = get_supabase_client(use_service_role=True)

    try:
        query = supabase.table("cake_options").select("*").order("type").order("sort_order")

        if type is not None:
            if type not in VALID_OPTION_TYPES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid type. Must be one of: {', '.join(VALID_OPTION_TYPES)}",
                )
            query = query.eq("type", type)

        if is_active is not None:
            query = query.eq("is_active", is_active)

        result = query.execute()
        return {"options": result.data or [], "total": len(result.data or [])}

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to fetch cake options")


@router.post("", status_code=201)
def create_option(
    request: CreateOptionRequest,
    current_user: dict = Depends(require_admin),
):
    """
    Create a new cake option.

    Validates option type and required fields.
    Requires Admin role.
    """
    if request.type not in VALID_OPTION_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid type. Must be one of: {', '.join(VALID_OPTION_TYPES)}",
        )

    supabase = get_supabase_client(use_service_role=True)

    try:
        data = {
            "type": request.type,
            "name": request.name,
            "label": request.label,
            "price_modifier": request.price_modifier,
            "sort_order": request.sort_order,
            "is_active": request.is_active,
        }
        if request.icon is not None:
            data["icon"] = request.icon
        if request.hex_color is not None:
            data["hex_color"] = request.hex_color

        result = supabase.table("cake_options").insert(data).execute()

        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create option")

        return JSONResponse(status_code=201, content=result.data[0])

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e).lower()
        if "unique" in error_msg or "duplicate" in error_msg:
            raise HTTPException(
                status_code=409,
                detail=f"Option with name '{request.name}' already exists for type '{request.type}'",
            )
        raise HTTPException(status_code=500, detail="Failed to create option")


@router.put("/{option_id}")
def update_option(
    option_id: str,
    request: UpdateOptionRequest,
    current_user: dict = Depends(require_admin),
):
    """
    Update an existing cake option.

    Only provided fields will be updated.
    Requires Admin role.
    """
    supabase = get_supabase_client(use_service_role=True)

    try:
        update_data = {}
        if request.name is not None:
            update_data["name"] = request.name
        if request.label is not None:
            update_data["label"] = request.label
        if request.price_modifier is not None:
            update_data["price_modifier"] = request.price_modifier
        if request.sort_order is not None:
            update_data["sort_order"] = request.sort_order
        if request.icon is not None:
            update_data["icon"] = request.icon
        if request.hex_color is not None:
            update_data["hex_color"] = request.hex_color
        if request.is_active is not None:
            update_data["is_active"] = request.is_active

        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        result = (
            supabase.table("cake_options")
            .update(update_data)
            .eq("id", option_id)
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Option not found")

        return result.data[0]

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to update option")


@router.delete("/{option_id}", status_code=204)
def delete_option(
    option_id: str,
    current_user: dict = Depends(require_admin),
):
    """
    Delete a cake option.

    Permanently removes the option. Consider using PATCH /status to deactivate instead.
    Requires Admin role.
    """
    supabase = get_supabase_client(use_service_role=True)

    try:
        result = (
            supabase.table("cake_options")
            .delete()
            .eq("id", option_id)
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Option not found")

        return None

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to delete option")


@router.patch("/{option_id}/status")
def toggle_option_status(
    option_id: str,
    request: ToggleStatusRequest,
    current_user: dict = Depends(require_admin),
):
    """
    Toggle cake option active/inactive status.

    Deactivating hides the option from the public Cake Builder
    without deleting the database record.
    Requires Admin role.
    """
    supabase = get_supabase_client(use_service_role=True)

    try:
        result = (
            supabase.table("cake_options")
            .update({"is_active": request.is_active})
            .eq("id", option_id)
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Option not found")

        return result.data[0]

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to update option status")
