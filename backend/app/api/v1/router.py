"""API v1 router aggregating all service routers."""

from fastapi import APIRouter

from app.api.v1.endpoints import admin_products, auth, catalog

router = APIRouter()

# Auth service
router.include_router(auth.router, prefix="/auth", tags=["Auth"])

# Catalog service
router.include_router(catalog.router, prefix="/products", tags=["Catalog"])

# Admin product management
router.include_router(admin_products.router, prefix="/admin/products", tags=["Admin Products"])

# Service routers will be included here as they are implemented:
# from app.api.v1.endpoints import orders, chat, reviews
# router.include_router(orders.router, prefix="/orders", tags=["Orders"])
# router.include_router(chat.router, prefix="/chat", tags=["Chat"])
# router.include_router(reviews.router, prefix="/reviews", tags=["Reviews"])
