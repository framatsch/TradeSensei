"""Pydantic DTOs for authentication token request and response shapes."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    """Response schema returned by the token and refresh endpoints.

    Attributes:
        access_token: Signed JWT string to be sent as a Bearer token.
        token_type: Always ``"bearer"`` per OAuth2 convention.
    """

    access_token: str = Field(
        ...,
        description=(
            "Signed JWT access token. Include in the "
            "'Authorization: Bearer <token>' header."
        ),
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
