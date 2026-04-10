"""Async repository for cached OHLC price bars."""

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ohlc_price import OhlcPrice


class OhlcPriceRepository:
    """Data-access object for cached OHLC price rows.

    Args:
        session: Database session used for all read and write operations.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the repository with an existing async session.

        Args:
            session: Database session used for all repository calls.
        """
        self._session = session

    async def get_cached_prices(
        self,
        symbol: str,
        interval: str,
        provider: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[OhlcPrice]:
        """Return cached OHLC bars matching the requested range.

        Args:
            symbol: Ticker symbol to load.
            interval: Candle interval (for example ``"1d"``).
            provider: Market data provider identifier.
            start: Inclusive lower bound for bar start timestamps.
            end: Inclusive upper bound for bar start timestamps.

        Returns:
            Matching cached bars ordered ascending by start timestamp.
        """
        stmt = select(OhlcPrice).where(
            OhlcPrice.symbol == symbol,
            OhlcPrice.interval == interval,
            OhlcPrice.provider == provider,
        )
        if start is not None:
            stmt = stmt.where(OhlcPrice.start >= start)
        if end is not None:
            stmt = stmt.where(OhlcPrice.start <= end)

        result = await self._session.execute(stmt.order_by(OhlcPrice.start.asc()))
        return list(result.scalars().all())

    async def upsert_bars(self, bars: list[dict[str, Any]]) -> None:
        """Insert or update OHLC bars in a single bulk operation.

        Args:
            bars: Normalized bar payloads ready for persistence.
        """
        if not bars:
            return

        stmt = insert(OhlcPrice).values(bars)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_ohlc_price_bar",
            set_={
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "volume": stmt.excluded.volume,
                "meta": stmt.excluded.meta,
            },
        )
        await self._session.execute(stmt)
        await self._session.flush()
