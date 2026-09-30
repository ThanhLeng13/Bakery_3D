"""Public API for the reusable birthday-cake 3D model warehouse."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.core.dependencies import get_supabase_client
from app.schemas.cake_3d_models import Cake3DModelListResponse, Cake3DModelResponse
from app.services.cake_3d_model_service import (
    Cake3DModelNotFoundError,
    Cake3DModelService,
    Cake3DModelServiceError,
)

router = APIRouter()


def _get_service() -> Cake3DModelService:
    """Use anon client because the warehouse is intentionally public read-only."""
    return Cake3DModelService(get_supabase_client(use_service_role=False))


@router.get("", response_model=Cake3DModelListResponse)
def list_cake_3d_models(
    category: Optional[str] = Query(default=None, min_length=1, max_length=50),
    tag: Optional[str] = Query(default=None, min_length=1, max_length=50),
):
    """List active 3D cake bases for the builder and product-detail viewer."""
    try:
        return _get_service().list_models(category=category, tag=tag)
    except Cake3DModelServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


@router.get("/{model_id}", response_model=Cake3DModelResponse)
def get_cake_3d_model(model_id: str):
    """Get one active model by its UUID or stable slug."""
    try:
        return _get_service().get_model(model_id)
    except Cake3DModelNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message)
    except Cake3DModelServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
