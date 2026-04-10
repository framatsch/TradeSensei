"""Schemas for market data API responses."""

from pydantic import BaseModel


class OHLCBar(BaseModel):
    """Single OHLC bar returned by the market data endpoint."""

    symbol: str
    start: str
    open: str
    high: str
    low: str
    close: str
    volume: float
    provider: str


class OHLCResponse(BaseModel):
    """Envelope for OHLC history responses."""

    data: list[OHLCBar]
