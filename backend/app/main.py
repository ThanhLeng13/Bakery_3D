"""FastAPI application entry point for Cake Shop AI API."""

import traceback

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import (
    generate_request_id,
    get_logger,
    request_id_ctx,
    setup_logging,
)

# Initialize structured logging
setup_logging(log_level="DEBUG" if settings.DEBUG else "INFO")

logger = get_logger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        description="API backend cho hệ thống Web Bán Bánh Kem Tích Hợp AI",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
    )

    # CORS middleware — phai add truoc cac middleware khac de bao phu ca 500 errors
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    # Global exception handler — dam bao 500 luon tra CORS header
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(
            "unhandled_exception",
            path=str(request.url.path),
            error=str(exc),
            traceback=traceback.format_exc(),
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    # Request ID middleware
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next) -> Response:
        """Attach a unique request_id to each request for log correlation."""
        req_id = request.headers.get("X-Request-ID") or generate_request_id()
        token = request_id_ctx.set(req_id)

        logger.info(
            "request_started",
            method=request.method,
            path=str(request.url.path),
        )

        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = req_id

            logger.info(
                "request_completed",
                method=request.method,
                path=str(request.url.path),
                status_code=response.status_code,
            )
            return response
        except Exception as exc:
            logger.error(
                "middleware_exception",
                path=str(request.url.path),
                error=str(exc),
                traceback=traceback.format_exc(),
            )
            # Phai them CORS headers thu cong vi response nay khong di qua CORSMiddleware
            # (do exception thoat qua call_next trong BaseHTTPMiddleware).
            origin = request.headers.get("origin", "")
            cors_headers = {
                "Access-Control-Allow-Origin": origin if ("*" in settings.CORS_ORIGINS or origin in settings.CORS_ORIGINS) else "",
                "Access-Control-Allow-Credentials": "true",
                "Vary": "Origin",
            }
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"},
                headers={k: v for k, v in cors_headers.items() if v},
            )
        finally:
            request_id_ctx.reset(token)

    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Health check endpoint for container orchestration."""
        return {"status": "healthy", "app": settings.APP_NAME, "env": settings.APP_ENV}

    # Include API v1 router
    from app.api.v1.router import router as api_v1_router

    app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

    # API v1 root endpoint
    @app.get(f"{settings.API_V1_PREFIX}/", tags=["Root"])
    async def api_root():
        """API v1 root endpoint."""
        return {"message": "Cake Shop AI API v1", "docs": "/docs"}

    return app


app = create_app()
