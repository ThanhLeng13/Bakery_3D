from typing import Optional
from app.core.config import settings

def format_image_url(url: Optional[str]) -> Optional[str]:
    """
    Format a storage URL into a fully-qualified Supabase URL if it's a storage path,
    otherwise return the URL as-is.
    """
    if not url:
        return None
    if url.startswith("/storage/") or url.startswith("storage/"):
        base_url = settings.SUPABASE_URL.rstrip("/")
        path = url.lstrip("/")
        return f"{base_url}/{path}"
    return url
