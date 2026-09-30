"""Business logic for the public 3D cake-model warehouse."""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class Cake3DModelServiceError(Exception):
    """Known public 3D-model service error."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class Cake3DModelNotFoundError(Cake3DModelServiceError):
    """Requested active 3D model does not exist."""

    def __init__(self, model_id: str):
        super().__init__(f"3D cake model not found: {model_id}", status_code=404)


_MODEL_FIELDS = "id, slug, name, glb_url, thumbnail_url, tags, category, created_at"


class Cake3DModelService:
    """Read-only public queries for reusable birthday-cake .glb assets."""

    def __init__(self, supabase_client: Any):
        self._supabase = supabase_client

    def list_models(
        self,
        category: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> dict:
        """List active model assets, optionally narrowed by category or one tag."""
        try:
            query = (
                self._supabase.table("cake_3d_models")
                .select(_MODEL_FIELDS, count="exact")
                .eq("is_active", True)
                .order("name")
            )
            if category:
                query = query.eq("category", category)
            if tag:
                # PostgREST contains: tags contains the one-element array [tag].
                query = query.contains("tags", [tag])

            result = query.execute()
            models = result.data or []
            return {"models": models, "total": result.count or len(models)}
        except Exception as exc:
            logger.exception("Failed to list 3D cake models")
            raise Cake3DModelServiceError("Failed to fetch 3D cake models", status_code=500) from exc

    def get_model(self, model_id: str) -> dict:
        """Return one active model by UUID or stable slug."""
        try:
            by_id = (
                self._supabase.table("cake_3d_models")
                .select(_MODEL_FIELDS)
                .eq("id", model_id)
                .eq("is_active", True)
                .maybe_single()
                .execute()
            )
            if by_id.data:
                return by_id.data
        except Exception:
            # A non-UUID id causes PostgREST to reject the UUID comparison. It is
            # expected for a slug, so fall through to the slug query below.
            pass

        try:
            by_slug = (
                self._supabase.table("cake_3d_models")
                .select(_MODEL_FIELDS)
                .eq("slug", model_id)
                .eq("is_active", True)
                .maybe_single()
                .execute()
            )
            if by_slug.data:
                return by_slug.data
        except Exception as exc:
            logger.exception("Failed to fetch 3D cake model", extra={"model_id": model_id})
            raise Cake3DModelServiceError("Failed to fetch 3D cake model", status_code=500) from exc

        raise Cake3DModelNotFoundError(model_id)
