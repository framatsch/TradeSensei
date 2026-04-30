"""SQLAlchemy ORM model for caching OHLC price data."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, Index, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import NUMERIC_PRECISION, NUMERIC_SCALE, SYMBOL_MAX_LENGTH
from app.core.database import Base


class OhlcPrice(Base):
    """ORM representation of a cached OHLC price bar.

    This table stores price history fetched from external providers (like LSEG)
    to avoid redundant API calls and stay within rate limits.

    Attributes:
        id: BigInt primary key (auto-increment).
        symbol: Ticker symbol (e.g. ``"AAPL"``).
        interval: Bar interval (e.g. ``"1h"``, ``"4h"``, ``"1d"``).
        provider: Source of the data (e.g. ``"lseg"``).
        start: Timestamp of the bar's open.
        open: Opening price.
        high: Highest price during the interval.
        low: Lowest price during the interval.
        close: Closing price.
        volume: Traded volume during the interval.
        meta: Optional additional data from the provider.
        created_at: When this bar was first cached.
    """

    __tablename__ = "ohlc_prices"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(SYMBOL_MAX_LENGTH), nullable=False)
    interval: Mapped[str] = mapped_column(String(10), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    open: Mapped[Decimal] = mapped_column(Numeric(NUMERIC_PRECISION, NUMERIC_SCALE), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(NUMERIC_PRECISION, NUMERIC_SCALE), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(NUMERIC_PRECISION, NUMERIC_SCALE), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(NUMERIC_PRECISION, NUMERIC_SCALE), nullable=False)
    volume: Mapped[Decimal | None] = mapped_column(Numeric(NUMERIC_PRECISION, NUMERIC_SCALE), nullable=True)

    meta: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("symbol", "interval", "provider", "start", name="uq_ohlc_price_bar"),
        Index("ix_ohlc_prices_symbol_interval", "symbol", "interval"),
        Index("ix_ohlc_prices_start", "start"),
    )

    def __repr__(self) -> str:
        """Return a debug string for the OHLC bar."""
        return f"<OhlcPrice symbol={self.symbol!r} interval={self.interval!r} start={self.start}>"
