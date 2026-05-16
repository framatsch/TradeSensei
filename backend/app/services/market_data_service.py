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

"""Service for fetching and caching OHLC price data."""

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ohlc_price import OhlcPrice
from app.repositories.ohlc_price_repository import OhlcPriceRepository


class MarketDataService:
    """Service for managing OHLC price data with a database cache."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the service with a database session.

        Args:
            session: Async SQLAlchemy session.
        """
        self._repo = OhlcPriceRepository(session)

    async def get_cached_prices(
        self,
        symbol: str,
        interval: str,
        provider: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[OhlcPrice]:
        """Retrieve OHLC bars from the local cache as ORM models.

        Args:
            symbol: Ticker symbol.
            interval: Bar interval (1h, 1d, etc.).
            provider: Data source name.
            start: Optional start timestamp filter.
            end: Optional end timestamp filter.

        Returns:
            A list of OhlcPrice ORM models.
        """
        return await self._repo.get_cached_prices(
            symbol=symbol,
            interval=interval,
            provider=provider,
            start=start,
            end=end,
        )

    def format_bars(self, bars: list[OhlcPrice]) -> list[dict[str, Any]]:
        """Format OHLC bars for the frontend.

        Args:
            bars: List of OhlcPrice ORM models.

        Returns:
            A list of bar dictionaries formatted for the frontend.
        """
        return [
            {
                "symbol": b.symbol,
                "start": b.start.isoformat().replace("+00:00", "Z"),
                "open": str(b.open),
                "high": str(b.high),
                "low": str(b.low),
                "close": str(b.close),
                "volume": float(b.volume) if b.volume is not None else 0,
                "provider": b.provider,
            }
            for b in bars
        ]

    async def cache_prices(self, bars: list[dict[str, Any]]) -> None:
        """Upsert a list of OHLC bars into the database cache.

        Args:
            bars: List of bar dictionaries from the provider.
        """
        if not bars:
            return

        # Prepare values for upsert
        values = []
        for b in bars:
            # Parse ISO string to datetime
            start_dt = datetime.fromisoformat(b["start"].replace("Z", "+00:00"))
            values.append(
                {
                    "symbol": b["symbol"],
                    "interval": b.get("interval", "1d"),  # Fallback if missing
                    "provider": b["provider"],
                    "start": start_dt,
                    "open": b["open"],
                    "high": b["high"],
                    "low": b["low"],
                    "close": b["close"],
                    "volume": b.get("volume"),
                    "meta": b.get("meta"),
                }
            )

        await self._repo.upsert_bars(values)
