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

"""Pydantic DTOs for Playbook request and response shapes."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.core.constants import (
    PLAYBOOK_DESCRIPTION_MAX_LENGTH,
    PLAYBOOK_NAME_MAX_LENGTH,
    PLAYBOOK_NAME_MIN_LENGTH,
)
from app.schemas.taxonomy import TaxonomyResponse


class PlaybookCreate(BaseModel):
    """Request schema for creating a new playbook.

    Attributes:
        name: Human-readable playbook name (unique per user).
        description: Optional long-form description of the strategy.
    """

    name: str = Field(
        ...,
        min_length=PLAYBOOK_NAME_MIN_LENGTH,
        max_length=PLAYBOOK_NAME_MAX_LENGTH,
        description=("Human-readable playbook name, unique per user. For example: 'Breakout Long', 'Mean Reversion'."),
        examples=["Breakout Long", "VWAP Fade"],
    )
    description: str | None = Field(
        default=None,
        max_length=PLAYBOOK_DESCRIPTION_MAX_LENGTH,
        description=("Optional long-form description of the strategy or setup. Maximum 2 000 characters."),
        examples=["Enter on a confirmed breakout above the prior day high.", None],
    )
    content_markdown: str | None = Field(
        default=None,
        description="Optional detailed markdown content for the playbook.",
    )
    target_winrate: Decimal | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Target winrate as a decimal between 0 and 1.",
        examples=[Decimal("0.5500")],
    )


class PlaybookUpdate(BaseModel):
    """Request schema for partially updating an existing playbook.

    All fields are optional — only supplied fields will be written.

    Attributes:
        name: Updated playbook name.
        description: Updated description.
        is_active: Updated active flag.
    """

    name: str | None = Field(
        default=None,
        min_length=PLAYBOOK_NAME_MIN_LENGTH,
        max_length=PLAYBOOK_NAME_MAX_LENGTH,
        description="Updated playbook name. Omit to leave unchanged.",
        examples=["Breakout Short", None],
    )
    description: str | None = Field(
        default=None,
        max_length=PLAYBOOK_DESCRIPTION_MAX_LENGTH,
        description=("Updated description. Omit to leave unchanged. Set to null to clear the existing description."),
        examples=["Revised criteria for entry.", None],
    )
    content_markdown: str | None = Field(
        default=None,
        description="Updated markdown content.",
    )
    target_winrate: Decimal | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Updated target winrate.",
    )
    is_active: bool | None = Field(
        default=None,
        description="Updated active flag. Omit to leave unchanged.",
        examples=[False, None],
    )


class PlaybookRead(BaseModel):
    """Response schema for a single playbook.

    Attributes:
        id: UUID primary key.
        user_id: UUID of the owning user.
        name: Playbook label.
        description: Optional description.
        is_active: Whether the playbook is active.
        created_at: UTC timestamp of playbook creation.
        updated_at: UTC timestamp of the last update.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(
        ...,
        description="Unique playbook identifier (UUID v4).",
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    )
    user_id: uuid.UUID = Field(
        ...,
        description="UUID of the user who owns this playbook.",
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    )
    name: str = Field(
        ...,
        description="Human-readable playbook label.",
        examples=["Breakout Long"],
    )
    description: str | None = Field(
        ...,
        description="Optional strategy description. Null if not set.",
        examples=["Enter on a confirmed breakout above prior day high.", None],
    )
    content_markdown: str | None = Field(
        ...,
        description="Detailed markdown content.",
    )
    target_winrate: Decimal | None = Field(
        ...,
        description="Target winrate as a decimal between 0 and 1.",
    )
    is_active: bool = Field(
        ...,
        description="Whether this playbook is currently active.",
        examples=[True],
    )
    created_at: AwareDatetime = Field(
        ...,
        description="UTC timestamp of playbook creation.",
        examples=["2024-03-15T09:30:00Z"],
    )
    updated_at: datetime = Field(
        ...,
        description="UTC timestamp of the most recent update to this playbook.",
        examples=["2024-03-15T10:00:00Z"],
    )
    taxonomies: list[TaxonomyResponse] = Field(
        default_factory=list,
        description="Taxonomy tags assigned to this playbook.",
    )

    @model_validator(mode="before")
    @classmethod
    def _resolve_taxonomies(cls, data: Any) -> Any:
        """Flatten taxonomy_assignments relationship into taxonomies list."""
        if isinstance(data, dict):
            return data
        if hasattr(data, "taxonomy_assignments") and not hasattr(data, "taxonomies"):
            data.__dict__["taxonomies"] = [
                a.taxonomy
                for a in data.taxonomy_assignments
                if getattr(a, "taxonomy", None) is not None
            ]
        return data
