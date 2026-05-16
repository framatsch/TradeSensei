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

"""Pydantic schemas for annotation definitions and assignment payloads."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ScopeType = Literal["trades", "checkins", "both"]
AnnotationType = Literal["int", "float", "bool", "string_enum"]


class AnnotationDefinitionCreate(BaseModel):
    """Payload for creating an annotation definition."""

    name: str = Field(..., min_length=1, max_length=100, description="Unique annotation name within a scope.")
    type: AnnotationType = Field(..., description="Value type: int, float, bool, or string_enum.")
    scope: ScopeType = Field(..., description="Assignment scope: trades, checkins, or both.")
    description: str | None = Field(default=None, max_length=500, description="Optional annotation description.")
    scale_labels: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Optional type-specific metadata. For string_enum use scale_labels.options; "
            "for int/float, optional scale_labels.min and scale_labels.max are supported."
        ),
    )
    icon_identifier: str | None = Field(
        default=None,
        max_length=100,
        description="Optional icon identifier (for example 'lucide:brain').",
    )


class AnnotationDefinitionUpdate(BaseModel):
    """Payload for updating an annotation definition."""

    name: str | None = Field(default=None, min_length=1, max_length=100, description="Updated annotation name.")
    type: AnnotationType | None = Field(default=None, description="Updated annotation type.")
    scope: ScopeType | None = Field(default=None, description="Updated assignment scope.")
    description: str | None = Field(default=None, max_length=500, description="Updated annotation description.")
    scale_labels: dict[str, Any] | None = Field(
        default=None,
        description="Updated type-specific metadata.",
    )
    icon_identifier: str | None = Field(
        default=None,
        max_length=100,
        description="Updated icon identifier or null to clear.",
    )


class AnnotationDefinitionResponse(BaseModel):
    """Response schema for annotation definitions."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Annotation definition identifier.")
    name: str = Field(..., description="Annotation definition name.")
    type: AnnotationType = Field(..., description="Annotation value type.")
    scope: ScopeType = Field(..., description="Assignment scope.")
    description: str | None = Field(..., description="Optional annotation description.")
    scale_labels: dict[str, Any] | None = Field(..., description="Optional type-specific metadata.")
    icon_identifier: str | None = Field(..., description="Optional icon identifier.")
    is_archived: bool = Field(..., description="Archived flag.")
    created_at: datetime = Field(..., description="UTC creation timestamp.")
    updated_at: datetime = Field(..., description="UTC update timestamp.")


class AnnotationAssignRequest(BaseModel):
    """Payload for assigning/updating annotation values."""

    value: Any = Field(..., description="Raw value; type validation is performed in the service layer.")


class TradeAnnotationResponse(BaseModel):
    """Resolved annotation payload returned in trade detail responses."""

    model_config = ConfigDict(from_attributes=True)

    annotation_definition_id: uuid.UUID = Field(..., description="Annotation definition UUID.")
    name: str = Field(..., description="Annotation definition name.")
    type: AnnotationType = Field(..., description="Annotation value type.")
    scope: ScopeType = Field(..., description="Annotation definition scope.")
    icon_identifier: str | None = Field(..., description="Optional icon identifier from definition.")
    value: Any = Field(..., description="Resolved typed value.")


class CheckinAnnotationResponse(BaseModel):
    """Resolved annotation payload returned in check-in detail responses."""

    model_config = ConfigDict(from_attributes=True)

    annotation_definition_id: uuid.UUID = Field(..., description="Annotation definition UUID.")
    name: str = Field(..., description="Annotation definition name.")
    type: AnnotationType = Field(..., description="Annotation value type.")
    scope: ScopeType = Field(..., description="Annotation definition scope.")
    icon_identifier: str | None = Field(..., description="Optional icon identifier from definition.")
    value: Any = Field(..., description="Resolved typed value.")
