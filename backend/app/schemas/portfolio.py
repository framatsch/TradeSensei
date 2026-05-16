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

"""Pydantic DTOs for Portfolio request and response shapes."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

PortfolioBaseCurrency = Literal["USD", "EUR", "GBP", "CHF", "JPY", "AUD", "CAD"]


class PortfolioCreate(BaseModel):
    """Request schema for creating a portfolio."""

    name: str = Field(..., min_length=1, max_length=100)
    base_currency: PortfolioBaseCurrency
    color_hex: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")


class PortfolioUpdate(BaseModel):
    """Request schema for partially updating a portfolio."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    base_currency: PortfolioBaseCurrency | None = None
    color_hex: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")


class PortfolioRead(BaseModel):
    """Response schema for portfolios."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    base_currency: PortfolioBaseCurrency
    color_hex: str | None
    created_at: datetime
    updated_at: datetime
