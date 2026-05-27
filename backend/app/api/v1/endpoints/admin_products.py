"""Admin product management API endpoints.

Endpoints:
- POST   /api/v1/admin/products              - Create product
- PUT    /api/v1/admin/products/{id}         - Update product
- PATCH  /api/v1/admin/products/{id}/status  - Toggle active status
- POST   /api/v1/admin/products/{id}/images  - Upload product image

All endpoints require Admin role authentication.
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.core.dependencies import require_admin, get_supabase_client
from app.schemas.admin_products import (
    CreateProductRequest,
    UpdateProductRequest,
    UpdateProductStatusRequest,
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
