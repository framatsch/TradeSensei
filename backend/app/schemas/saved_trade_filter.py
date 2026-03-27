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
