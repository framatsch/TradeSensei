"""Pydantic DTOs for User request and response shapes."""

import uuid

from pydantic import AwareDatetime, BaseModel, ConfigDict, EmailStr, Field

from app.core.constants import (
    PASSWORD_MIN_LENGTH,
    USERNAME_MAX_LENGTH,
    USERNAME_MIN_LENGTH,
)


class UserCreate(BaseModel):
    """Request schema for registering a new user.

    Attributes:
        username: Chosen display name (3–50 characters).
        email: Valid email address used for login.
        password: Plain-text password (min 8 characters, write-only).
    """

    username: str = Field(
        ...,
        min_length=USERNAME_MIN_LENGTH,
        max_length=USERNAME_MAX_LENGTH,
        description="Unique display name (3–50 characters).",
        examples=["alice", "trader_bob"],
    )
    email: EmailStr = Field(
        ...,
        description="Valid email address used for authentication.",
        examples=["alice@example.com"],
    )
    password: str = Field(
        ...,
        min_length=PASSWORD_MIN_LENGTH,
        description=(
            "Plain-text password (minimum 8 characters). Never stored or returned."
        ),
        examples=["S3cur3P@ss!"],
    )


class UserRead(BaseModel):
    """Response schema for a single user.

    The ``hashed_password`` field is intentionally omitted.

    Attributes:
        id: UUID primary key.
        username: Display name.
        email: Email address.
        is_active: Whether the user account is active.
        created_at: UTC timestamp of account creation.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(
        ...,
        description="Unique user identifier (UUID v4).",
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    )
    username: str = Field(
        ...,
        description="Display name.",
        examples=["alice"],
    )
    email: str = Field(
        ...,
        description="Email address.",
        examples=["alice@example.com"],
    )
    is_active: bool = Field(
        ...,
        description="Whether this user account is currently active.",
        examples=[True],
    )
    created_at: AwareDatetime = Field(
        ...,
        description="UTC timestamp of account creation.",
        examples=["2024-03-15T09:30:00Z"],
    )


class UserUpdate(BaseModel):
    """Request schema for partially updating the current user's profile.

    All fields are optional — only supplied fields are written.

    Attributes:
        username: Updated display name.
        email: Updated email address.
    """

    username: str | None = Field(
        default=None,
        min_length=USERNAME_MIN_LENGTH,
        max_length=USERNAME_MAX_LENGTH,
        description="Updated display name. Omit to leave unchanged.",
        examples=["alice_v2", None],
    )
    email: EmailStr | None = Field(
        default=None,
        description="Updated email address. Omit to leave unchanged.",
        examples=["newalice@example.com", None],
    )


class UserLogin(BaseModel):
    """Request schema for the JSON-body login endpoint.

    Callers may identify themselves with either ``username`` or ``email``.

    Attributes:
        username: Username or email used to identify the account.
        password: Plain-text password.
    """

    username: str = Field(
        ...,
        description="Username or email address of the account to authenticate.",
        examples=["alice", "alice@example.com"],
    )
    password: str = Field(
        ...,
        description="Plain-text password.",
        examples=["S3cur3P@ss!"],
    )
