"""API v1 router aggregating all service routers."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin_orders, admin_products, auth, baker_orders,
    branches, catalog, chat, inventory, orders, purchases, reviews,
)

router = APIRouter()

# Auth service
router.include_router(auth.router, prefix="/auth", tags=["Auth"])

# Branches — public list of store branches
router.include_router(branches.router, prefix="/branches", tags=["Branches"])

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

# Review service - POST /reviews and GET /products/{id}/reviews (nested under catalog prefix)
router.include_router(reviews.router, prefix="", tags=["Reviews"])

# Inventory — baker batch management + public stock query
router.include_router(inventory.baker_router, prefix="/baker", tags=["Baker Inventory"])
router.include_router(inventory.public_router, prefix="", tags=["Stock"])

# Purchases — direct sweet purchase (trừ stock ngay)
router.include_router(purchases.router, prefix="/purchases", tags=["Purchases"])
