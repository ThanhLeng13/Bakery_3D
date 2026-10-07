"""Pydantic schemas for the public 3D cake-model warehouse."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class Cake3DModelResponse(BaseModel):
    """One reusable .glb asset in the 3D cake warehouse."""

    id: UUID
    slug: str
    name: str
    glb_url: str
    thumbnail_url: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    category: str
    created_at: datetime


class Cake3DModelListResponse(BaseModel):
    """Public list response for the active 3D cake-model warehouse."""

    models: List[Cake3DModelResponse] = Field(default_factory=list)
    total: int = 0


class Product3DModelResponse(Cake3DModelResponse):
    """Warehouse asset linked to one catalog product."""

    sort_order: int = 0
    is_primary: bool = False
    # False when the model is preview-only: viewable in the Studio, but the
    # bakery has not approved its price and lead time for production, so the
    # order is refused server-side.
    is_orderable: bool = True
