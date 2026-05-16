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


class MarketIndexDefinitionBase(BaseModel):
    """Base schema for Market Index Definition."""

    symbol: str = Field(..., max_length=50, description="The ticker symbol (e.g. SPX)")
    name: str = Field(..., max_length=100, description="The display name")
    tradingview_url: str | None = Field(None, max_length=255, description="Link to TV")
    is_active: bool = Field(True, description="Whether it is active")


class MarketIndexDefinitionCreate(MarketIndexDefinitionBase):
    """Schema for creating a Market Index Definition."""

    pass


class MarketIndexDefinitionUpdate(BaseModel):
    """Schema for updating a Market Index Definition."""

    symbol: str | None = Field(None, max_length=50)
    name: str | None = Field(None, max_length=100)
    tradingview_url: str | None = Field(None, max_length=255)
    is_active: bool | None = None


class MarketIndexDefinitionResponse(MarketIndexDefinitionBase):
    """Schema for returning a Market Index Definition."""

    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
