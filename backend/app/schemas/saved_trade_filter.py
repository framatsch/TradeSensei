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
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.saved_trade_filter import FilterScope


class SavedTradeFilterBase(BaseModel):
    """Base schema for saved trade filters."""

    name: str = Field(..., max_length=255)
    definition: dict[str, Any] = Field(default_factory=dict)


class SavedTradeFilterCreate(SavedTradeFilterBase):
    """Schema for creating a new user-owned saved trade filter."""

    pass


class SavedTradeFilterUpdate(BaseModel):
    """Schema for updating an existing user-owned saved trade filter."""

    name: str | None = Field(None, max_length=255)
    definition: dict[str, Any] | None = None


class SavedTradeFilterRead(SavedTradeFilterBase):
    """Schema for reading a saved trade filter."""

    id: UUID
    scope: FilterScope
    owner_id: UUID | None
    needs_review: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
