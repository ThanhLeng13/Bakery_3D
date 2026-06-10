"""FastAPI dependencies for authentication and role-based access control.

Provides:
- get_current_user: Extracts JWT from Authorization header, validates via Supabase, returns user dict
- require_role: Dependency factory that checks if current user has one of the required roles
- require_admin: Shortcut for require_role(["admin"])
- require_baker: Shortcut for require_role(["baker"])
- require_customer: Shortcut for require_role(["customer"])
"""

import logging
import threading

from typing import Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

# HTTPBearer scheme extracts token from "Authorization: Bearer <token>" header
# auto_error=False so we can return a custom 401 message
security_scheme = HTTPBearer(auto_error=False)

# ─── Thread-local Supabase client cache ────────────────────────────────────────
# supabase-py is NOT thread-safe for concurrent requests on a shared client.
# Using threading.local() gives each worker thread its own cached client instance,
# avoiding both (a) cross-thread race conditions and (b) the overhead of creating
# a new HTTP connection (TLS handshake, socket) on every single request.
_thread_local = threading.local()


def get_supabase_client(token: str | None = None, use_service_role: bool = False):
    """Thread-safe Supabase client factory with per-thread caching.

    Each thread in the ASGI thread pool gets its own client instance stored in
    threading.local(). This avoids connection exhaustion under load while
    maintaining thread safety (no shared mutable state across threads).

    Per-request auth tokens are applied via postgrest.auth() on the cached client
    without creating a new connection.
    """
    from supabase import create_client

    if use_service_role:
        if not getattr(settings, "SUPABASE_SERVICE_ROLE_KEY", None):
            raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is not configured.")
        # Cache service-role client per thread
        client = getattr(_thread_local, "service_client", None)
        if client is None:
            client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
            _thread_local.service_client = client
        return client

    # Cache anon client per thread
    client = getattr(_thread_local, "anon_client", None)
    if client is None:
        client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        _thread_local.anon_client = client

    # CRITICAL: Always set auth state on cached client.
    # If token is provided → authenticate this request.
    # If token is None → CLEAR previous request's token to prevent
    # cross-request privilege escalation on the same thread.
    if token:
        client.postgrest.auth(token)
    else:
        client.postgrest.auth("")
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
            supabase_admin = _get_supabase_admin_client()
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
            # User exists in auth but not in users table - treat as customer
            return {
                "id": str(supabase_user.id),
                "email": supabase_user.email,
                "full_name": "",
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
