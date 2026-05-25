from typing import Optional
from app.core.config import settings

def format_image_url(url: Optional[str]) -> Optional[str]:
    """
    Format a storage URL into a fully-qualified Supabase URL.
    Handles relative paths, standard Supabase public storage prefixes,
    and returns absolute URLs as-is.
    """
    if not url:
        return None
        
    if url.startswith("http://") or url.startswith("https://"):
        return url
        
    base_url = settings.SUPABASE_URL.rstrip("/")
    path = url.lstrip("/")
    
    # Check if path already contains the standard storage API prefix
    if "storage/v1/object/public/" in path:
        idx = path.find("storage/v1/object/public/")
        subpath = path[idx:]
        return f"{base_url}/{subpath}"
    else:
        # Otherwise, assume it's just the bucket and file path (e.g. product-images/uuid/file.jpg)
        return f"{base_url}/storage/v1/object/public/{path}"
