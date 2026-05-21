"""Pydantic schemas for authentication endpoints."""

import re
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    """Registration request schema."""

    email: EmailStr = Field(..., max_length=254, description="Email address")
    password: str = Field(
        ..., min_length=8, max_length=128, description="Password"
    )
    full_name: str = Field(
        ..., min_length=1, max_length=100, description="Full name"
    )
    phone: str = Field(..., min_length=10, max_length=10, description="Phone number (10-digit Vietnamese format)")

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        """Password must contain at least one uppercase, one lowercase, and one digit."""
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone_format(cls, v: str) -> str:
        """Phone must be exactly 10 digits (Vietnamese format)."""
        if not re.match(r"^\d{10}$", v):
            raise ValueError("Phone must be exactly 10 digits")
        return v


class LoginRequest(BaseModel):
    """Login request schema."""

    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., description="Password")


class GoogleOAuthRequest(BaseModel):
    """Google OAuth2 callback request schema."""

    access_token: str = Field(..., description="Google OAuth2 access token")


class RefreshTokenRequest(BaseModel):
    """Token refresh request schema."""

    refresh_token: str = Field(..., description="Refresh token")


class LogoutRequest(BaseModel):
    """Logout request schema."""

    access_token: str = Field(..., description="Access token to invalidate")


class AuthResponse(BaseModel):
    """Authentication response with tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    user: "UserResponse"


class UserResponse(BaseModel):
    """User information in auth response."""

    id: str
    email: str
    full_name: str
    phone: Optional[str] = None
    role: str = "customer"


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str
