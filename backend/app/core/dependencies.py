"""FastAPI dependencies for authentication and role-based access control.

Provides:
- get_current_user: Extracts JWT from Authorization header, validates via Supabase, returns user dict
- require_role: Dependency factory that checks if current user has one of the required roles
- require_admin: Shortcut for require_role(["admin"])
- require_baker: Shortcut for require_role(["baker"])
- require_customer: Shortcut for require_role(["customer"])
"""

import logging
import contextvars

from typing import Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

# HTTPBearer scheme extracts token from "Authorization: Bearer <token>" header
# auto_error=False so we can return a custom 401 message
security_scheme = HTTPBearer(auto_error=False)

# ─── ContextVar-based Supabase client cache ─────────────────────────────────────────────────
# contextvars.ContextVar provides per-task (and per-thread) isolation in ASGI apps.
# Unlike threading.local(), a ContextVar is task-local: concurrent async requests
# running on the same OS thread each get their own context, preventing client
# cache sharing and auth-token leaks across requests.
_ctx_anon_client: contextvars.ContextVar = contextvars.ContextVar("supabase_anon_client", default=None)
_ctx_service_client: contextvars.ContextVar = contextvars.ContextVar("supabase_service_client", default=None)


def get_supabase_client(token: str | None = None, use_service_role: bool = False):
    """Context-safe Supabase client factory with per-task caching.

    Uses contextvars.ContextVar so that each asyncio task (i.e. each concurrent
    ASGI request) gets its own cached client, even when multiple tasks run on the
    same OS thread. This is the correct standard for FastAPI/ASGI environments and
    prevents auth-token leaks that threading.local() cannot guard against.

    Per-request auth tokens: for authenticated requests a fresh Supabase client
    is instantiated and the token is applied via postgrest.auth(). This avoids
    mutating a shared cached client, which would risk token leaks across tasks.
    """
    from supabase import create_client

    if use_service_role:
        if not getattr(settings, "SUPABASE_SERVICE_ROLE_KEY", None):
            raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is not configured.")
        # Cache service-role client per task context
        client = _ctx_service_client.get(None)
        if client is None:
            client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
            _ctx_service_client.set(client)
        return client

    # Unauthenticated path: reuse cached anon client (no mutation)
    if not token:
        client = _ctx_anon_client.get(None)
        if client is None:
            client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            _ctx_anon_client.set(client)
        return client

    # Authenticated path: create a fresh client per request.
    # We intentionally do NOT cache or mutate the shared anon client here.
    # Mutating a cached client with .auth(token) is unsafe because:
    # (a) forgetting to clear it leaks auth to the next unauthenticated request,
    # (b) clearing with .auth("") can race with concurrent async tasks.
    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    client.postgrest.auth(token)
    return client


def _get_supabase_client(token: str | None = None):
    """Get Supabase client instance for auth validation."""
    return get_supabase_client(token, use_service_role=False)


def _get_supabase_admin_client():
    """Get Supabase client instance with service role key for admin database queries."""
    return get_supabase_client(use_service_role=True)



def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> dict:
    """
    Extract and validate JWT token from the Authorization header.

    Uses Supabase's get_user() to validate the token, then fetches
    the user's role from the users table.

    Returns:
        dict with user info: id, email, full_name, phone, role

    Raises:
        HTTPException 401: If token is missing, invalid, or expired
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        supabase = _get_supabase_client(token)

        # Validate token via Supabase Auth - this checks expiry and signature
        user_response = supabase.auth.get_user(token)

        if user_response is None or user_response.user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        supabase_user = user_response.user

        # Fetch user role from users table using admin client to bypass RLS
        try:
            supabase_admin = get_supabase_client(use_service_role=True)
        except Exception as init_err:
            logging.getLogger(__name__).error(
                "Failed to initialize admin client: %s",
                str(init_err),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error initializing admin client",
            )

        try:
            user_result = (
                supabase_admin.table("users")
                .select("id, email, full_name, phone, role")
                .eq("id", str(supabase_user.id))
                .maybe_single()
                .execute()
            )
        except Exception as db_err:
            logging.getLogger(__name__).error(
                "Failed to query users table for user %s: %s",
                supabase_user.id,
                str(db_err),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            )


        if user_result is None or user_result.data is None:
            # User exists in auth but not in users table.
            # Auto-create the profile so that FK constraints (e.g. orders.customer_id)
            # are satisfied. This covers Google OAuth users whose on_auth_user_created
            # trigger may not have fired, or accounts created outside the app.
            user_id = str(supabase_user.id)
            user_email = supabase_user.email or None
            full_name = ""
            if supabase_user.user_metadata:
                full_name = (
                    supabase_user.user_metadata.get("full_name")
                    or supabase_user.user_metadata.get("name")
                    or ""
                )
            try:
                supabase_admin.table("users").upsert(
                    {
                        "id": user_id,
                        "email": user_email,
                        "full_name": full_name,
                        "role": "customer",
                    },
                    on_conflict="id",
                ).execute()
            except Exception as upsert_err:
                logging.getLogger(__name__).warning(
                    "Could not auto-create user profile for %s: %s",
                    user_id,
                    str(upsert_err),
                )
            return {
                "id": user_id,
                "email": user_email,
                "full_name": full_name,
                "phone": None,
                "role": "customer",
            }

        return {
            "id": user_result.data["id"],
            "email": user_result.data["email"],
            "full_name": user_result.data.get("full_name", ""),
            "phone": user_result.data.get("phone"),
            "role": user_result.data.get("role", "customer"),
        }

    except HTTPException:
        raise
    except Exception:
        # Any Supabase auth error (expired, invalid, network) → 401
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_role(roles: list[str]) -> Callable:
    """
    Dependency factory that checks if the current user has one of the required roles.

    Usage:
        @router.get("/admin/products", dependencies=[Depends(require_role(["admin"]))])
        async def list_products(): ...

        # Or inject the user:
        @router.get("/admin/products")
        async def list_products(user: dict = Depends(require_role(["admin"]))): ...

    Args:
        roles: List of allowed role strings (e.g., ["admin"], ["admin", "baker"])

    Returns:
        A FastAPI dependency that validates the user's role.

    Raises:
        HTTPException 401: If token is missing/invalid/expired
        HTTPException 403: If user's role is not in the allowed roles
    """

    def role_checker(
        current_user: dict = Depends(get_current_user),
    ) -> dict:
        user_role = current_user.get("role", "")
        if user_role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return role_checker


# Convenience shortcuts for common role checks
require_admin = require_role(["admin"])
require_baker = require_role(["baker"])
require_customer = require_role(["customer"])
