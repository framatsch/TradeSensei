"""Pydantic schemas for taxonomy definitions and assignments."""

import re
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

_HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

ScopeType = Literal["trades", "checkins", "playbook", "both"]


class TaxonomyCreate(BaseModel):
    """Payload for creating a taxonomy definition."""

    name: str = Field(..., min_length=1, max_length=100, description="Unique taxonomy name within a scope.")
    scope: ScopeType = Field(..., description="Assignment scope: trades, checkins, or both.")
    color_hex: str = Field(..., description="Hex color in #RRGGBB format.")
    description: str | None = Field(default=None, max_length=500, description="Optional taxonomy description.")
    icon_identifier: str | None = Field(
        default=None,
        max_length=100,
        description="Optional icon identifier (for example 'lucide:trending-down').",
    )

    @field_validator("color_hex")
    @classmethod
    def validate_hex_color(cls, value: str) -> str:
        """Validate color as #RRGGBB."""
        if not _HEX_COLOR_RE.fullmatch(value):
            raise ValueError("color_hex must match #RRGGBB")
        return value


class TaxonomyUpdate(BaseModel):
    """Payload for updating a taxonomy definition."""

    name: str | None = Field(default=None, min_length=1, max_length=100, description="Updated taxonomy name.")
    scope: ScopeType | None = Field(default=None, description="Updated assignment scope.")
    color_hex: str | None = Field(default=None, description="Updated hex color in #RRGGBB format.")
    description: str | None = Field(default=None, max_length=500, description="Updated description.")
    icon_identifier: str | None = Field(
        default=None,
        max_length=100,
        description="Updated icon identifier or null to clear.",
    )

    @field_validator("color_hex")
    @classmethod
    def validate_hex_color(cls, value: str | None) -> str | None:
        """Validate color as #RRGGBB when provided."""
        if value is None:
            return None
        if not _HEX_COLOR_RE.fullmatch(value):
            raise ValueError("color_hex must match #RRGGBB")
        return value


class TaxonomyResponse(BaseModel):
    """Response schema for taxonomy definitions."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Taxonomy identifier.")
    name: str = Field(..., description="Taxonomy name.")
    scope: ScopeType = Field(..., description="Assignment scope.")
    color_hex: str = Field(..., description="Hex color in #RRGGBB format.")
    description: str | None = Field(..., description="Optional taxonomy description.")
    icon_identifier: str | None = Field(..., description="Optional icon identifier.")
    is_archived: bool = Field(..., description="Archived flag.")
    created_at: datetime = Field(..., description="UTC creation timestamp.")
    updated_at: datetime = Field(..., description="UTC update timestamp.")


class TaxonomyAssignRequest(BaseModel):
    """Payload for assigning taxonomy to an entity."""

    taxonomy_id: uuid.UUID = Field(..., description="Taxonomy definition UUID to assign.")
