# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Pydantic schemas for taxonomy definitions and assignments."""

import re
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

_HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

class TaxonomyCreate(BaseModel):
    """Payload for creating a taxonomy definition."""

    name: str = Field(..., min_length=1, max_length=100, description="Unique taxonomy name within a scope.")
    scope: str = Field(..., description="Comma-separated assignment scope (e.g. 'trades,checkins').")
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
    scope: str | None = Field(default=None, description="Updated comma-separated assignment scope.")
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
    scope: str = Field(..., description="Assignment scope.")
    color_hex: str = Field(..., description="Hex color in #RRGGBB format.")
    description: str | None = Field(..., description="Optional taxonomy description.")
    icon_identifier: str | None = Field(..., description="Optional icon identifier.")
    is_archived: bool = Field(..., description="Archived flag.")
    created_at: datetime = Field(..., description="UTC creation timestamp.")
    updated_at: datetime = Field(..., description="UTC update timestamp.")


class TaxonomyAssignRequest(BaseModel):
    """Payload for assigning taxonomy to an entity."""

    taxonomy_id: uuid.UUID = Field(..., description="Taxonomy definition UUID to assign.")
