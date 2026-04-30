"""Pydantic DTOs for Tag request and response shapes."""

import uuid

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.core.constants import TAG_NAME_MAX_LENGTH, TAG_NAME_MIN_LENGTH


class TagCreate(BaseModel):
    """Request schema for creating a new tag.

    Attributes:
        name: Tag label (unique per user).
        color: Optional hex colour string (e.g. ``"#3b82f6"``).
    """

    name: str = Field(
        ...,
        min_length=TAG_NAME_MIN_LENGTH,
        max_length=TAG_NAME_MAX_LENGTH,
        description=("Tag label, unique per user. Maximum 50 characters. For example: 'gap-and-go', 'revenge-trade', 'oversize'."),
        examples=["gap-and-go", "revenge-trade", "high-conviction"],
    )
    color: str | None = Field(
        default=None,
        pattern=r"^#[0-9a-fA-F]{6}$",
        description=("Optional hex colour for UI display. Must match the pattern ``#RRGGBB`` (e.g. ``'#3b82f6'``). Omit or set to null for no colour."),
        examples=["#3b82f6", "#ef4444", None],
    )


class TagUpdate(BaseModel):
    """Request schema for partially updating an existing tag.

    All fields are optional — only supplied fields will be written.

    Attributes:
        name: Updated tag label.
        color: Updated hex colour.
    """

    name: str | None = Field(
        default=None,
        min_length=TAG_NAME_MIN_LENGTH,
        max_length=TAG_NAME_MAX_LENGTH,
        description="Updated tag label. Omit to leave unchanged.",
        examples=["breakout", None],
    )
    color: str | None = Field(
        default=None,
        pattern=r"^#[0-9a-fA-F]{6}$",
        description=("Updated hex colour. Omit to leave unchanged. Set to null to remove the colour."),
        examples=["#22c55e", None],
    )


class TagRead(BaseModel):
    """Response schema for a single tag.

    Attributes:
        id: UUID primary key.
        user_id: UUID of the owning user.
        name: Tag label.
        color: Hex colour string (``None`` if not set).
        created_at: UTC timestamp of tag creation.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(
        ...,
        description="Unique tag identifier (UUID v4).",
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    )
    user_id: uuid.UUID = Field(
        ...,
        description="UUID of the user who owns this tag.",
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    )
    name: str = Field(
        ...,
        description="Tag label.",
        examples=["gap-and-go"],
    )
    color: str | None = Field(
        ...,
        description="Hex colour for UI display. Null if not set.",
        examples=["#3b82f6", None],
    )
    created_at: AwareDatetime = Field(
        ...,
        description="UTC timestamp of tag creation.",
        examples=["2024-03-15T09:30:00Z"],
    )
