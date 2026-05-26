"""API v1 router aggregating all service routers."""

from fastapi import APIRouter

from app.api.v1.endpoints import admin_orders, admin_products, auth, baker_orders, catalog, chat, orders, reviews

router = APIRouter()

# Auth service
router.include_router(auth.router, prefix="/auth", tags=["Auth"])

# Catalog service
router.include_router(catalog.router, prefix="/products", tags=["Catalog"])

# Admin product management
router.include_router(admin_products.router, prefix="/admin/products", tags=["Admin Products"])

# Admin order management
router.include_router(admin_orders.router, prefix="/admin/orders", tags=["Admin Orders"])

# Baker order management
router.include_router(baker_orders.router, prefix="/baker/orders", tags=["Baker Orders"])

# Chat service (AI Chatbot)
router.include_router(chat.router, prefix="/chat", tags=["Chat"])

# Order service
router.include_router(orders.router, prefix="/orders", tags=["Orders"])

# Review service - POST /reviews and GET /products/{id}/reviews
router.include_router(reviews.router, prefix="/reviews", tags=["Reviews"])

