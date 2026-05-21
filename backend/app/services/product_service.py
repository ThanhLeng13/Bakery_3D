"""Product management service - business logic layer.

Handles product CRUD operations, image upload/processing, and catalog revalidation.
"""

import io
import uuid
from typing import Any, Optional

from PIL import Image

from app.core.config import settings


class ProductServiceError(Exception):
    """Base exception for product service errors."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class ProductValidationError(ProductServiceError):
    """Validation error with field-level details."""

    def __init__(self, errors: list[dict[str, str]]):
        self.errors = errors
        super().__init__("Validation failed", status_code=422)


class ProductNotFoundError(ProductServiceError):
    """Product not found error."""

    def __init__(self, product_id: str):
        super().__init__(f"Product not found: {product_id}", status_code=404)


# Allowed image MIME types and extensions
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}

MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5MB
MAX_IMAGE_DIMENSION = 1200  # pixels
IMAGE_BUCKET = "product-images"


class ProductService:
    """Service for product management operations."""

    def __init__(self, supabase_client: Any):
        """Initialize with a Supabase client instance (service role)."""
        self._supabase = supabase_client

    async def create_product(self, data: dict) -> dict:
        """
        Create a new product.

        Args:
            data: Product data with name, description, category, base_price, sizes, flavors, is_active

        Returns:
            Created product record

        Raises:
            ProductValidationError: If validation fails
            ProductServiceError: If creation fails
        """
        try:
            # Prepare sizes as JSON-serializable list
            sizes_json = [{"name": s["name"], "price": s["price"]} for s in data["sizes"]]

            product_data = {
                "name": data["name"],
                "description": data["description"],
                "category": data["category"],
                "base_price": data["base_price"],
                "sizes": sizes_json,
                "flavors": data.get("flavors", []),
                "is_active": data.get("is_active", True),
            }

            result = (
                self._supabase.table("products")
                .insert(product_data)
                .execute()
            )

            if not result.data:
                raise ProductServiceError("Failed to create product", status_code=500)

            product = result.data[0]

            # Fetch images (empty for new product)
            product["images"] = []

            return product

        except ProductServiceError:
            raise
        except Exception as e:
            error_msg = str(e).lower()
            if "duplicate" in error_msg or "unique" in error_msg:
                raise ProductValidationError(
                    [{"field": "name", "message": "A product with this name already exists"}]
                )
            raise ProductServiceError(f"Failed to create product: {str(e)}", status_code=500)

    async def update_product(self, product_id: str, data: dict) -> dict:
        """
        Update an existing product.

        Args:
            product_id: UUID of the product to update
            data: Fields to update (only non-None fields)

        Returns:
            Updated product record

        Raises:
            ProductNotFoundError: If product doesn't exist
            ProductServiceError: If update fails
        """
        # Verify product exists
        await self._get_product_or_raise(product_id)

        try:
            update_data = {}

            if data.get("name") is not None:
                update_data["name"] = data["name"]
            if data.get("description") is not None:
                update_data["description"] = data["description"]
            if data.get("category") is not None:
                update_data["category"] = data["category"]
            if data.get("base_price") is not None:
                update_data["base_price"] = data["base_price"]
            if data.get("sizes") is not None:
                update_data["sizes"] = [{"name": s["name"], "price": s["price"]} for s in data["sizes"]]
            if data.get("flavors") is not None:
                update_data["flavors"] = data["flavors"]
            if data.get("is_active") is not None:
                update_data["is_active"] = data["is_active"]

            if not update_data:
                # Nothing to update, return current product
                return await self._get_product_with_images(product_id)

            result = (
                self._supabase.table("products")
                .update(update_data)
                .eq("id", product_id)
                .execute()
            )

            if not result.data:
                raise ProductServiceError("Failed to update product", status_code=500)

            # Trigger catalog revalidation
            await self._trigger_revalidation(product_id)

            return await self._get_product_with_images(product_id)

        except (ProductServiceError, ProductNotFoundError):
            raise
        except Exception as e:
            raise ProductServiceError(f"Failed to update product: {str(e)}", status_code=500)

    async def toggle_status(self, product_id: str, is_active: bool) -> dict:
        """
        Toggle product active status.

        Args:
            product_id: UUID of the product
            is_active: New active status

        Returns:
            Updated product record

        Raises:
            ProductNotFoundError: If product doesn't exist
        """
        await self._get_product_or_raise(product_id)

        try:
            result = (
                self._supabase.table("products")
                .update({"is_active": is_active})
                .eq("id", product_id)
                .execute()
            )

            if not result.data:
                raise ProductServiceError("Failed to update product status", status_code=500)

            # Trigger catalog revalidation
            await self._trigger_revalidation(product_id)

            return await self._get_product_with_images(product_id)

        except (ProductServiceError, ProductNotFoundError):
            raise
        except Exception as e:
            raise ProductServiceError(f"Failed to toggle status: {str(e)}", status_code=500)

    async def upload_image(
        self,
        product_id: str,
        file_content: bytes,
        content_type: str,
        filename: str,
    ) -> dict:
        """
        Upload and process a product image.

        Steps:
        1. Validate file type and size
        2. Resize image to max 1200x1200 preserving aspect ratio
        3. Upload to Supabase Storage (product-images bucket)
        4. Create product_images record

        Args:
            product_id: UUID of the product
            file_content: Raw file bytes
            content_type: MIME type of the file
            filename: Original filename

        Returns:
            Product image record with URL

        Raises:
            ProductNotFoundError: If product doesn't exist
            ProductValidationError: If image validation fails
        """
        # Verify product exists
        await self._get_product_or_raise(product_id)

        # Validate content type
        if content_type not in ALLOWED_IMAGE_TYPES:
            raise ProductValidationError(
                [{"field": "image", "message": "Unsupported format. Use JPEG, PNG, or WebP"}]
            )

        # Validate file size
        if len(file_content) > MAX_IMAGE_SIZE_BYTES:
            raise ProductValidationError(
                [{"field": "image", "message": "File exceeds 5MB limit"}]
            )

        try:
            # Process image: resize to max 1200x1200 preserving aspect ratio
            processed_content, output_content_type = self._process_image(file_content, content_type)

            # Generate unique filename for storage
            ext = ALLOWED_IMAGE_TYPES[output_content_type]
            storage_filename = f"{product_id}/{uuid.uuid4().hex}.{ext}"

            # Upload to Supabase Storage
            self._supabase.storage.from_(IMAGE_BUCKET).upload(
                path=storage_filename,
                file=processed_content,
                file_options={"content-type": output_content_type},
            )

            # Get public URL
            public_url = self._supabase.storage.from_(IMAGE_BUCKET).get_public_url(storage_filename)

            # Get current max sort_order for this product
            existing_images = (
                self._supabase.table("product_images")
                .select("sort_order")
                .eq("product_id", product_id)
                .order("sort_order", desc=True)
                .limit(1)
                .execute()
            )

            next_sort_order = 0
            if existing_images.data:
                next_sort_order = existing_images.data[0]["sort_order"] + 1

            # Create product_images record
            image_data = {
                "product_id": product_id,
                "url": public_url,
                "sort_order": next_sort_order,
            }

            result = (
                self._supabase.table("product_images")
                .insert(image_data)
                .execute()
            )

            if not result.data:
                raise ProductServiceError("Failed to save image record", status_code=500)

            # Trigger catalog revalidation
            await self._trigger_revalidation(product_id)

            return result.data[0]

        except (ProductServiceError, ProductValidationError, ProductNotFoundError):
            raise
        except Exception as e:
            raise ProductServiceError(f"Failed to upload image: {str(e)}", status_code=500)

    def _process_image(self, file_content: bytes, content_type: str) -> tuple[bytes, str]:
        """
        Resize image to max 1200x1200 preserving aspect ratio.

        Args:
            file_content: Raw image bytes
            content_type: MIME type

        Returns:
            Tuple of (processed bytes, content_type)
        """
        try:
            image = Image.open(io.BytesIO(file_content))

            # Convert RGBA to RGB for JPEG
            if image.mode == "RGBA" and content_type == "image/jpeg":
                background = Image.new("RGB", image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[3])
                image = background
            elif image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGB")

            # Resize if larger than max dimension
            if image.width > MAX_IMAGE_DIMENSION or image.height > MAX_IMAGE_DIMENSION:
                image.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION), Image.LANCZOS)

            # Save to bytes
            output = io.BytesIO()
            if content_type == "image/jpeg":
                image.save(output, format="JPEG", quality=85, optimize=True)
            elif content_type == "image/png":
                image.save(output, format="PNG", optimize=True)
            elif content_type == "image/webp":
                image.save(output, format="WEBP", quality=85)
            else:
                image.save(output, format="JPEG", quality=85, optimize=True)
                content_type = "image/jpeg"

            return output.getvalue(), content_type

        except Exception as e:
            raise ProductValidationError(
                [{"field": "image", "message": f"Invalid image file: {str(e)}"}]
            )

    async def _get_product_or_raise(self, product_id: str) -> dict:
        """Fetch product by ID or raise ProductNotFoundError."""
        try:
            result = (
                self._supabase.table("products")
                .select("*")
                .eq("id", product_id)
                .maybe_single()
                .execute()
            )

            if result.data is None:
                raise ProductNotFoundError(product_id)

            return result.data

        except ProductNotFoundError:
            raise
        except Exception as e:
            raise ProductServiceError(f"Failed to fetch product: {str(e)}", status_code=500)

    async def _get_product_with_images(self, product_id: str) -> dict:
        """Fetch product with its images."""
        product = await self._get_product_or_raise(product_id)

        # Fetch images
        images_result = (
            self._supabase.table("product_images")
            .select("*")
            .eq("product_id", product_id)
            .order("sort_order")
            .execute()
        )

        product["images"] = images_result.data if images_result.data else []
        return product

    async def _trigger_revalidation(self, product_id: str) -> None:
        """
        Trigger catalog revalidation after product update.

        For Phase 1, relies on ISR TTL (60s) for automatic revalidation.
        In production, this would call the Next.js on-demand revalidation API.
        """
        # Phase 1: Rely on ISR TTL (60s) for catalog revalidation.
        # The Next.js frontend uses ISR with 60s revalidation period,
        # so changes will be reflected within 60 seconds.
        #
        # Future enhancement: Call Next.js revalidation API endpoint
        # POST {FRONTEND_URL}/api/revalidate?tag=products&secret={REVALIDATION_SECRET}
        pass
