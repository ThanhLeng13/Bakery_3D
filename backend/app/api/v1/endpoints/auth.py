"""Authentication API endpoints.

Endpoints:
- POST /api/v1/auth/register - Register new customer
- POST /api/v1/auth/login - Login with email/password
- POST /api/v1/auth/oauth/google - Google OAuth2 callback
- POST /api/v1/auth/refresh - Refresh JWT token
- POST /api/v1/auth/logout - Logout
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from app.core.dependencies import get_supabase_client
from app.schemas.auth import (
    AuthResponse,
    ForgotPasswordRequest,
    GoogleOAuthRequest,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
)
from app.services.auth_service import (
    AuthService,
    AuthServiceError,
    RateLimitError,
    ValidationError,
)

router = APIRouter()


def _get_auth_service() -> AuthService:
    """Create AuthService with Supabase client."""
    client = get_supabase_client(use_service_role=False)
    return AuthService(client)


def _handle_auth_error(e: AuthServiceError) -> JSONResponse:
    """Convert AuthServiceError to appropriate HTTP response."""
    if isinstance(e, ValidationError):
        return JSONResponse(
            status_code=422,
            content={"detail": e.errors},
        )
    if isinstance(e, RateLimitError):
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Too many attempts. Please try again later.",
                "retry_after": e.retry_after,
            },
        )
    return JSONResponse(
        status_code=e.status_code,
        content={"detail": e.message},
    )


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(request: RegisterRequest):
    """
    Register a new customer account.

    Validates email, password complexity, full name, and phone format.
    Creates user in Supabase Auth and users table with 'customer' role.
    """
    auth_service = _get_auth_service()

    try:
        result = await auth_service.register(
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            phone=request.phone,
        )
        return JSONResponse(status_code=201, content=result)
    except (ValidationError, RateLimitError, AuthServiceError) as e:
        return _handle_auth_error(e)


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """
    Login with email and password.

    Rate limited: max 5 failed attempts per 15-minute window per email.
    15-minute lockout after exceeding the limit.
    """
    auth_service = _get_auth_service()

    try:
        result = await auth_service.login(
            email=request.email,
            password=request.password,
        )
        return result
    except (ValidationError, RateLimitError, AuthServiceError) as e:
        return _handle_auth_error(e)


@router.post("/oauth/google", response_model=AuthResponse)
async def oauth_google(request: GoogleOAuthRequest):
    """
    Authenticate via Google OAuth2.

    Links to existing account if email matches, or creates new account.
    """
    auth_service = _get_auth_service()

    try:
        result = await auth_service.oauth_google(
            access_token=request.access_token,
        )
        return result
    except (ValidationError, RateLimitError, AuthServiceError) as e:
        return _handle_auth_error(e)


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh JWT token.

    Used for auto-refresh when token has <5 minutes remaining.
    Issues a new access token with 1-hour expiration.
    """
    auth_service = _get_auth_service()

    try:
        result = await auth_service.refresh_token(
            refresh_token=request.refresh_token,
        )
        return result
    except (ValidationError, RateLimitError, AuthServiceError) as e:
        return _handle_auth_error(e)


@router.post("/logout", response_model=MessageResponse)
async def logout(request: LogoutRequest):
    """
    Logout and invalidate the session.

    Revokes the token via Supabase Auth.
    """
    auth_service = _get_auth_service()

    try:
        result = await auth_service.logout(
            access_token=request.access_token,
        )
        return result
    except (ValidationError, RateLimitError, AuthServiceError) as e:
        return _handle_auth_error(e)


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(request: ForgotPasswordRequest):
    """
    Request a password reset email.

    Sends an email with a reset link if the email is registered.
    Always returns success to prevent email enumeration attacks.
    Rate limited by Supabase (max 2 emails per hour).
    """
    auth_service = _get_auth_service()

    try:
        result = await auth_service.forgot_password(email=request.email)
        return result
    except (ValidationError, RateLimitError, AuthServiceError) as e:
        return _handle_auth_error(e)


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(request: ResetPasswordRequest):
    """
    Reset password using the token from reset email.

    The access_token is extracted from the URL fragment by the frontend
    (#access_token=...) after user clicks the Supabase-sent email link.
    Validates password complexity before updating.
    """
    auth_service = _get_auth_service()

    try:
        result = await auth_service.reset_password(
            access_token=request.access_token,
            new_password=request.new_password,
        )
        return result
    except (ValidationError, RateLimitError, AuthServiceError) as e:
        return _handle_auth_error(e)
