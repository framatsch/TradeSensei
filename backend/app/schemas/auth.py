"""Pydantic DTOs for authentication token request and response shapes."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.core.constants import PASSWORD_MIN_LENGTH


class TokenResponse(BaseModel):
    """Response schema returned by the token and refresh endpoints.

    Attributes:
        access_token: Signed JWT string to be sent as a Bearer token.
        token_type: Always ``"bearer"`` per OAuth2 convention.
    """

    access_token: str = Field(
        ...,
        description=("Signed JWT access token. Include in the 'Authorization: Bearer <token>' header."),
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    token_type: str = Field(
        default="bearer",
        description="Token type — always 'bearer'.",
        examples=["bearer"],
    )


class TokenPayload(BaseModel):
    """Internal schema for decoding a JWT payload.

    Attributes:
        sub: Subject claim — the user's UUID as a string.
        exp: Expiry timestamp embedded in the token.
    """

    sub: uuid.UUID = Field(
        ...,
        description="User UUID embedded as the JWT subject claim.",
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    )
    exp: datetime = Field(
        ...,
        description="Token expiry timestamp.",
        examples=["2024-03-15T09:45:00Z"],
    )


class OAuthExchangeRequest(BaseModel):
    """Request body for the OAuth one-time token exchange endpoint.

    After a successful Google OAuth callback the backend redirects the
    browser to the frontend with a short-lived one-time token in the
    query string.  The frontend posts that token here to receive a full
    access + refresh token pair.

    Attributes:
        one_time_token: The short-lived JWT from the OAuth redirect URL.
    """

    one_time_token: str = Field(
        ...,
        description=("Short-lived one-time JWT received via the OAuth callback redirect URL query parameter ``?token=``."),
    )


class OIDCConfig(BaseModel):
    """Configuration for generic OIDC provider.

    Attributes:
        enabled: Whether the OIDC provider is enabled.
        provider_name: Display name for the provider (e.g. "Authentik").
    """

    enabled: bool = Field(description="Whether the OIDC provider is enabled.")
    provider_name: str = Field(description="Display name for the provider.")


class AuthConfigResponse(BaseModel):
    """Response schema for available authentication methods.

    Attributes:
        google_enabled: Whether Google OAuth is configured and enabled.
        oidc: Configuration for generic OIDC.
        local_auth_enabled: Whether the local username/password login is enabled.
        password_reset_enabled: Whether self-service password reset via email is
            available (requires SMTP to be configured and local auth to be active).
    """

    google_enabled: bool = Field(description="Whether Google OAuth is enabled.")
    oidc: OIDCConfig = Field(description="OIDC configuration details.")
    local_auth_enabled: bool = Field(
        default=True,
        description="Whether the local username/password login form is enabled.",
    )
    password_reset_enabled: bool = Field(
        default=False,
        description=("Whether self-service password reset via email is available. Requires SMTP to be configured and local auth to be active."),
    )


class ForgotPasswordRequest(BaseModel):
    """Request body for the forgot-password endpoint.

    Attributes:
        email: Email address of the account to reset.
    """

    email: str = Field(
        ...,
        description="Email address associated with the account.",
        examples=["user@example.com"],
    )


class ResetPasswordRequest(BaseModel):
    """Request body for the reset-password endpoint.

    Attributes:
        token: The password-reset JWT from the email link.
        new_password: The new plain-text password to set.
    """

    token: str = Field(
        ...,
        description="Password-reset JWT received via email.",
    )
    new_password: str = Field(
        ...,
        min_length=PASSWORD_MIN_LENGTH,
        description=f"New password (minimum {PASSWORD_MIN_LENGTH} characters).",
    )
