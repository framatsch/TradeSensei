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

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CheckinFilterConfig(BaseModel):
    """Schema for the filter configuration JSONB payload."""

    regime: str | None = Field(default=None, description="Market regime filter")
    from_date: str | None = Field(default=None, description="Start date filter (YYYY-MM-DD)")
    to_date: str | None = Field(default=None, description="End date filter (YYYY-MM-DD)")
    target_indices: list[UUID] | None = Field(default=None, description="List of target index UUIDs to filter by")
    has_media: bool | None = Field(default=None, description="Filter for check-ins with media")


class SavedCheckinFilterBase(BaseModel):
    """Base schema for SavedCheckinFilter."""

    name: str = Field(..., max_length=255, description="Name of the saved filter")
    is_default: bool = Field(default=False, description="Whether this is the default view")
    filter_config: CheckinFilterConfig = Field(..., description="The filter configuration payload")


class SavedCheckinFilterCreate(SavedCheckinFilterBase):
    """Schema for creating a new SavedCheckinFilter."""
    pass


class SavedCheckinFilterUpdate(BaseModel):
    """Schema for updating an existing SavedCheckinFilter."""

    name: str | None = Field(default=None, max_length=255, description="Name of the saved filter")
    is_default: bool | None = Field(default=None, description="Whether this is the default view")
    filter_config: CheckinFilterConfig | None = Field(default=None, description="The filter configuration payload")


class SavedCheckinFilterResponse(SavedCheckinFilterBase):
    """Schema for returning a SavedCheckinFilter."""

    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
