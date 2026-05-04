"""Compatibility exports for market index schemas."""

from app.schemas.market_index import (
    MarketIndexDefinitionCreate,
    MarketIndexDefinitionResponse,
    MarketIndexDefinitionUpdate,
)

__all__ = [
    "MarketIndexDefinitionCreate",
    "MarketIndexDefinitionUpdate",
    "MarketIndexDefinitionResponse",
]
