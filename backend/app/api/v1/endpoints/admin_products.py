"""Admin product management API endpoints.

Endpoints:
- POST   /api/v1/admin/products              - Create product
- PUT    /api/v1/admin/products/{id}         - Update product
- PATCH  /api/v1/admin/products/{id}/status  - Toggle active status
- POST   /api/v1/admin/products/{id}/images  - Upload product image

All endpoints require Admin role authentication.
"""

from typing import Optional
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Query
from fastapi.responses import JSONResponse

from app.core.dependencies import require_admin, get_supabase_client
from app.utils.image_url import format_image_url
from app.schemas.admin_products import (
    CreateProductRequest,
    UpdateProductRequest,
    UpdateProductStatusRequest,
    ProductListResponse,
)
from app.services.product_service import (
    ProductNotFoundError,
    ProductService,
    ProductServiceError,
    ProductValidationError,
)

router = APIRouter()


def _get_product_service() -> ProductService:
    """Create ProductService with admin Supabase client."""
    client = get_supabase_client(use_service_role=True)
    return ProductService(client)


def _handle_product_error(e: ProductServiceError) -> JSONResponse:
    """Convert ProductServiceError to appropriate HTTP response."""
    if isinstance(e, ProductValidationError):
        return JSONResponse(
            status_code=422,
            content={"detail": e.errors},
        )
    if isinstance(e, ProductNotFoundError):
        return JSONResponse(
            status_code=404,
            content={"detail": "Product not found"},
        )
    return JSONResponse(
        status_code=e.status_code,
        content={"detail": e.message},
    )


@router.get("", response_model=ProductListResponse)
def list_admin_products(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
    current_user: dict = Depends(require_admin),
):
    """
    List all products for admin with pagination, search, and filtering.
    """
    supabase = get_supabase_client(use_service_role=True)
    try:
        # Base query for data and exact count in a single request
        offset = (page - 1) * page_size
        data_query = (
            supabase.table("products")
            .select("*, product_images(id, product_id, url, sort_order)", count="exact")
            .order("created_at", desc=True)
            .range(offset, offset + page_size - 1)
        )
        if search:
            data_query = data_query.ilike("name", f"%{search}%")
        if category:
            data_query = data_query.eq("category", category)
        if is_active is not None:
            data_query = data_query.eq("is_active", is_active)
            
        data_result = data_query.execute()
        products_data = data_result.data or []
        total = data_result.count if data_result.count is not None else 0
        
        # Format products to match ProductResponse
        formatted_products = []
        for p in products_data:
            images = p.get("product_images") or []
            images_sorted = sorted(images, key=lambda x: x.get("sort_order") or 0)
            
            formatted_images = []
            for img in images_sorted:
                formatted_images.append({
                    "id": img["id"],
                    "product_id": img["product_id"],
                    "url": format_image_url(img["url"]),
                    "sort_order": img.get("sort_order") or 0
                })
                
            formatted_products.append({
                "id": p["id"],
                "name": p["name"],
                "description": p.get("description"),
                "category": p["category"],
                "base_price": p["base_price"],
                "sizes": p.get("sizes") or [],
                "flavors": p.get("flavors") or [],
                "is_active": p["is_active"],
                "images": formatted_images,
                "created_at": p["created_at"].isoformat() if hasattr(p["created_at"], "isoformat") else str(p["created_at"]),
                "updated_at": p["updated_at"].isoformat() if hasattr(p["updated_at"], "isoformat") else str(p["updated_at"]),
            })
            
        return {
            "products": formatted_products,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Failed to fetch products")
        raise HTTPException(status_code=500, detail="Failed to fetch products")



@router.post("", status_code=201)
async def create_product(
    request: CreateProductRequest,
    current_user: dict = Depends(require_admin),
):
    """
    Create a new product.

    Validates:
    - name: 1-200 characters
    - description: 1-2000 characters
    - category: required
    - base_price: 1,000 - 999,999,999 VND
    - sizes: 1-10 options

    Requires Admin role.
    """
    service = _get_product_service()

    try:
        product_data = {
            "name": request.name,
            "description": request.description,
            "category": request.category,
            "base_price": request.base_price,
            "sizes": [{"name": s.name, "price": s.price} for s in request.sizes],
            "flavors": request.flavors,
            "is_active": request.is_active,
        }

        result = await service.create_product(product_data)
        return JSONResponse(status_code=201, content=result)

    except (ProductValidationError, ProductServiceError) as e:
        return _handle_product_error(e)


@router.put("/{product_id}")
async def update_product(
    product_id: str,
    request: UpdateProductRequest,
    current_user: dict = Depends(require_admin),
):
    """
    Update an existing product.

    Only provided fields will be updated. Triggers catalog revalidation.

    Requires Admin role.
    """
    service = _get_product_service()

    try:
        update_data = {}

        if request.name is not None:
            update_data["name"] = request.name
        if request.description is not None:
            update_data["description"] = request.description
        if request.category is not None:
            update_data["category"] = request.category
        if request.base_price is not None:
            update_data["base_price"] = request.base_price
        if request.sizes is not None:
            update_data["sizes"] = [{"name": s.name, "price": s.price} for s in request.sizes]
        if request.flavors is not None:
            update_data["flavors"] = request.flavors
        if request.is_active is not None:
            update_data["is_active"] = request.is_active

        result = await service.update_product(product_id, update_data)
        return result

    except (ProductValidationError, ProductNotFoundError, ProductServiceError) as e:
        return _handle_product_error(e)


@router.patch("/{product_id}/status")
async def toggle_product_status(
    product_id: str,
    request: UpdateProductStatusRequest,
    current_user: dict = Depends(require_admin),
):
    """
    Toggle product active status.

    Deactivating a product removes it from the customer-facing catalog
    without deleting the database record.

    Requires Admin role.
    """
    service = _get_product_service()

    try:
        result = await service.toggle_status(product_id, request.is_active)
        return result

    except (ProductNotFoundError, ProductServiceError) as e:
        return _handle_product_error(e)


@router.post("/{product_id}/images", status_code=201)
async def upload_product_image(
    product_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(require_admin),
):
    """
    Upload a product image.

    Validates:
    - Format: JPEG, PNG, or WebP only
    - Size: maximum 5MB
    - Resizes to max 1200x1200 pixels preserving aspect ratio

    Requires Admin role.
    """
    service = _get_product_service()

    # Validate content type from upload
    content_type = file.content_type or ""
    if content_type not in ("image/jpeg", "image/png", "image/webp"):
        return JSONResponse(
            status_code=415,
            content={"detail": "Unsupported format. Use JPEG, PNG, or WebP"},
        )

    try:
        # Read file content
        file_content = await file.read()

        # Validate file size
        if len(file_content) > 5 * 1024 * 1024:
            return JSONResponse(
                status_code=413,
                content={"detail": "File exceeds 5MB limit"},
            )

        result = await service.upload_image(
            product_id=product_id,
            file_content=file_content,
            content_type=content_type,
            filename=file.filename or "image",
        )

        return JSONResponse(status_code=201, content=result)

    except (ProductValidationError, ProductNotFoundError, ProductServiceError) as e:
        return _handle_product_error(e)
