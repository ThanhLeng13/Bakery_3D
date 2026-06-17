"""Public cake options API endpoint.

Endpoints:
- GET /api/v1/options - List active cake options (public, no auth required)

Used by the Cake Builder frontend to dynamically load available options
instead of relying on hardcoded constants.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.core.dependencies import get_supabase_client

router = APIRouter()


@router.get("")
def list_public_options(
    option_type: Optional[str] = Query(
        default=None,
        alias="type",
        description="Filter by type: size, flavor, topping, color"
    ),
):
    """
    List all active cake options (public endpoint, no authentication required).

    Returns active options sorted by sort_order for display in the Cake Builder.
    Groups results by type if no filter specified.
    """
    supabase = get_supabase_client(use_service_role=False)

    VALID_TYPES = {"size", "flavor", "topping", "color"}

    try:
        query = (
            supabase.table("cake_options")
            .select("id, type, name, label, price_modifier, sort_order, icon, hex_color")
            .eq("is_active", True)
            .order("sort_order")
        )

        if option_type is not None:
            if option_type not in VALID_TYPES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid type. Must be one of: {', '.join(VALID_TYPES)}",
                )
            query = query.eq("type", option_type)

        result = query.execute()
        options = result.data or []

        # Group by type if no filter
        if option_type is None:
            grouped: dict = {t: [] for t in VALID_TYPES}
            for opt in options:
                opt_type = opt.get("type")
                if opt_type in grouped:
                    grouped[opt_type].append(opt)
            return {"options": options, "grouped": grouped, "total": len(options)}

        return {"options": options, "total": len(options)}

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to fetch cake options")
