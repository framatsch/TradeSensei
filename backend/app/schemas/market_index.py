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
