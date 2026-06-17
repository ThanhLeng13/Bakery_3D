"""Authentication service - business logic layer.

Wraps Supabase Auth calls with validation and rate limiting.
"""

from typing import Any, Optional

from app.core.config import settings
from app.core.rate_limiter import login_rate_limiter
from app.core.security import validate_password


class AuthServiceError(Exception):
    """Base exception for auth service errors."""

    def __init__(self, message: str, status_code: int = 400, field: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.field = field
        super().__init__(message)


class ValidationError(AuthServiceError):
    """Validation error with field-level details."""

    def __init__(self, errors: list[dict[str, str]]):
        self.errors = errors
        super().__init__("Validation failed", status_code=422)


class RateLimitError(AuthServiceError):
    """Rate limit exceeded error."""

    def __init__(self, retry_after: int = 900):
        self.retry_after = retry_after
        super().__init__(
            "Too many failed login attempts. Please try again later.",
            status_code=429,
        )


class AuthService:
    """Authentication service handling registration, login, and token management."""

    def __init__(self, supabase_client: Any):
        """Initialize with a Supabase client instance."""
        self._supabase = supabase_client

    async def register(
        self,
        email: str,
        password: str,
        full_name: str,
        phone: str,
    ) -> dict:
        """
        Register a new customer account.

        Steps:
        1. Validate password complexity at API layer
        2. Create user in Supabase Auth
        3. Create user record in users table with 'customer' role
        4. Return auth tokens and user info
        """
        # Validate password complexity
        password_errors = validate_password(password)
        if password_errors:
            raise ValidationError(
                [{"field": "password", "message": msg} for msg in password_errors]
            )

        try:
            # Create user in Supabase Auth
            auth_response = self._supabase.auth.sign_up(
                {
                    "email": email,
                    "password": password,
                    "options": {
                        "data": {
                            "full_name": full_name,
                            "phone": phone,
                        }
                    },
                }
            )

            if auth_response.user is None:
                raise AuthServiceError(
                    "Registration failed. Please try again.",
                    status_code=500,
                )

            user_id = auth_response.user.id

            # Insert user record in users table with default 'customer' role
            user_data = {
                "id": user_id,
                "email": email,
                "full_name": full_name,
                "phone": phone,
                "role": "customer",
            }

            self._supabase.table("users").insert(user_data).execute()

            # Build response
            session = auth_response.session
            return {
                "access_token": session.access_token if session else "",
                "refresh_token": session.refresh_token if session else "",
                "token_type": "bearer",
                "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                "user": {
                    "id": user_id,
                    "email": email,
                    "full_name": full_name,
                    "phone": phone,
                    "role": "customer",
                },
            }

        except AuthServiceError:
            raise
        except Exception as e:
            error_msg = str(e).lower()
            if "already registered" in error_msg or "duplicate" in error_msg or "unique" in error_msg:
                raise ValidationError(
                    [{"field": "email", "message": "Email is already registered"}]
                )
            raise AuthServiceError(
                f"Registration failed: {str(e)}",
                status_code=500,
            )

    async def login(self, email: str, password: str) -> dict:
        """
        Login with email and password.

        Steps:
        1. Check rate limiting
        2. Authenticate via Supabase Auth
        3. On success: reset rate limiter, return tokens
        4. On failure: record failed attempt
        """
        # Check if account is locked
        if login_rate_limiter.is_locked(email):
            retry_after = login_rate_limiter.get_lockout_remaining(email)
            raise RateLimitError(retry_after=retry_after)

        try:
            # Authenticate via Supabase
            auth_response = self._supabase.auth.sign_in_with_password(
                {"email": email, "password": password}
            )

            if auth_response.user is None or auth_response.session is None:
                # Record failed attempt
                login_rate_limiter.record_failed_attempt(email)
                raise AuthServiceError(
                    "Invalid email or password",
                    status_code=401,
                )

            # Success - reset rate limiter
            login_rate_limiter.reset(email)

            # Fetch user role from users table
            user_result = (
                self._supabase.table("users")
                .select("*")
                .eq("id", auth_response.user.id)
                .single()
                .execute()
            )

            user_data = user_result.data if user_result.data else {}

            session = auth_response.session
            return {
                "access_token": session.access_token,
                "refresh_token": session.refresh_token,
                "token_type": "bearer",
                "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                "user": {
                    "id": str(auth_response.user.id),
                    "email": auth_response.user.email,
                    "full_name": user_data.get("full_name", ""),
                    "phone": user_data.get("phone"),
                    "role": user_data.get("role", "customer"),
                },
            }

        except (AuthServiceError, RateLimitError):
            raise
        except Exception as e:
            # Record failed attempt for any auth error
            login_rate_limiter.record_failed_attempt(email)
            raise AuthServiceError(
                "Invalid email or password",
                status_code=401,
            )

    async def oauth_google(self, access_token: str) -> dict:
        """
        Authenticate via Google OAuth2.

        Uses Supabase Auth to verify the Google token and either
        link to an existing account or create a new one.
        """
        try:
            # Sign in with Google ID token via Supabase
            auth_response = self._supabase.auth.sign_in_with_id_token(
                {"provider": "google", "token": access_token}
            )

            if auth_response.user is None or auth_response.session is None:
                raise AuthServiceError(
                    "Google authentication failed",
                    status_code=401,
                )

            user = auth_response.user
            session = auth_response.session

            # Check if user exists in users table
            user_result = (
                self._supabase.table("users")
                .select("*")
                .eq("id", user.id)
                .maybe_single()
                .execute()
            )

            if user_result is None:
                raise AuthServiceError(
                    "Unexpected server error",
                    status_code=500,
                )

            if user_result.data is None:
                # Create new user record with customer role
                user_metadata = user.user_metadata or {}
                user_data = {
                    "id": user.id,
                    "email": user.email,
                    "full_name": user_metadata.get("full_name", user_metadata.get("name", "")),
                    "phone": None,
                    "role": "customer",
                }
                self._supabase.table("users").insert(user_data).execute()
                role = "customer"
                full_name = user_data["full_name"]
                phone = None
            else:
                role = user_result.data.get("role", "customer")
                full_name = user_result.data.get("full_name", "")
                phone = user_result.data.get("phone")

            return {
                "access_token": session.access_token,
                "refresh_token": session.refresh_token,
                "token_type": "bearer",
                "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "full_name": full_name,
                    "phone": phone,
                    "role": role,
                },
            }

        except AuthServiceError:
            raise
        except Exception as e:
            raise AuthServiceError(
                "Google authentication failed",
                status_code=401,
            )

    async def refresh_token(self, refresh_token: str) -> dict:
        """
        Refresh an expired or near-expiry JWT token.

        Uses Supabase Auth to issue a new access token.
        """
        try:
            auth_response = self._supabase.auth.refresh_session(refresh_token)

            if auth_response.session is None:
                raise AuthServiceError(
                    "Invalid or expired refresh token",
                    status_code=401,
                )

            session = auth_response.session
            user = auth_response.user

            # Fetch user role
            user_result = (
                self._supabase.table("users")
                .select("*")
                .eq("id", user.id)
                .maybe_single()
                .execute()
            )

            user_data = user_result.data if (user_result and user_result.data) else {}

            return {
                "access_token": session.access_token,
                "refresh_token": session.refresh_token,
                "token_type": "bearer",
                "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "full_name": user_data.get("full_name", ""),
                    "phone": user_data.get("phone"),
                    "role": user_data.get("role", "customer"),
                },
            }

        except AuthServiceError:
            raise
        except Exception as e:
            raise AuthServiceError(
                "Token refresh failed",
                status_code=401,
            )

    async def forgot_password(self, email: str) -> dict:
        """
        Send a password reset email via Supabase Auth.

        Supabase will send an email with a magic link that redirects to
        the frontend reset-password page with access_token in URL fragment.
        Always returns success to prevent email enumeration attacks.
        """
        try:
            self._supabase.auth.reset_password_for_email(
                email,
                options={"redirect_to": f"{settings.FRONTEND_URL}/auth/reset-password"},
            )
        except Exception:
            # Silently ignore errors to prevent email enumeration
            pass
        return {"message": "If this email is registered, you will receive a reset link shortly."}

    async def reset_password(self, access_token: str, new_password: str) -> dict:
        """
        Reset user password using the token from the reset email.

        The access_token is extracted from the URL fragment by the frontend
        after the user clicks the Supabase reset link.
        """
        password_errors = validate_password(new_password)
        if password_errors:
            raise ValidationError(
                [{"field": "new_password", "message": msg} for msg in password_errors]
            )

        try:
            # Set the session using the token from the email link
            self._supabase.auth.set_session(access_token, access_token)
            # Update the password
            self._supabase.auth.update_user({"password": new_password})
            return {"message": "Password has been reset successfully. Please log in with your new password."}
        except AuthServiceError:
            raise
        except Exception as e:
            error_msg = str(e).lower()
            if "invalid" in error_msg or "expired" in error_msg or "jwt" in error_msg:
                raise AuthServiceError(
                    "Reset link is invalid or has expired. Please request a new one.",
                    status_code=401,
                )
            raise AuthServiceError(
                "Password reset failed. Please try again.",
                status_code=500,
            )

    async def logout(self, access_token: str) -> dict:
        """
        Logout and invalidate the session.

        Calls Supabase Auth to revoke the token.
        """
        try:
            self._supabase.auth.sign_out(access_token)
            return {"message": "Successfully logged out"}
        except Exception:
            # Even if sign_out fails, we consider it a success
            # The client should clear local tokens regardless
            return {"message": "Successfully logged out"}
