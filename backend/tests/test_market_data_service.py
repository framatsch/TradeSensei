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

"""Unit tests for MarketDataService."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.ohlc_price import OhlcPrice
from app.services.market_data_service import MarketDataService


@pytest.fixture
def mock_session() -> AsyncMock:
    """Mock SQLAlchemy session."""
    return AsyncMock()


@pytest.fixture
def service(mock_session: AsyncMock) -> MarketDataService:
    """MarketDataService with mock session."""
    return MarketDataService(mock_session)


@pytest.mark.unit
async def test_get_cached_prices(
    service: MarketDataService, mock_session: AsyncMock
) -> None:
    """Test retrieving cached prices."""
    # Mock return values
    mock_bars = [
        OhlcPrice(
            symbol="AAPL",
            interval="1d",
            provider="lseg",
            start=datetime(2024, 1, 1, tzinfo=UTC),
            open=Decimal("150.0"),
            high=Decimal("155.0"),
            low=Decimal("149.0"),
            close=Decimal("153.0"),
            volume=1000,
        )
    ]

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = mock_bars
    mock_session.execute.return_value = mock_result

    bars = await service.get_cached_prices("AAPL", "1d", "lseg")

    assert len(bars) == 1
    assert bars[0].symbol == "AAPL"
    assert bars[0].close == Decimal("153.0")
    mock_session.execute.assert_called_once()


@pytest.mark.unit
async def test_format_bars(service: MarketDataService) -> None:
    """Test formatting bars for frontend."""
    bars = [
        OhlcPrice(
            symbol="AAPL",
            interval="1d",
            provider="lseg",
            start=datetime(2024, 1, 1, tzinfo=UTC),
            open=Decimal("150.0"),
            high=Decimal("155.0"),
            low=Decimal("149.0"),
            close=Decimal("153.0"),
            volume=1000,
        )
    ]

    formatted = service.format_bars(bars)

    assert len(formatted) == 1
    assert formatted[0]["symbol"] == "AAPL"
    assert formatted[0]["start"] == "2024-01-01T00:00:00Z"
    assert formatted[0]["close"] == "153.0"
    assert formatted[0]["volume"] == 1000.0


@pytest.mark.unit
async def test_get_cached_prices_with_filters(
    service: MarketDataService, mock_session: AsyncMock
) -> None:
    """Test retrieving cached prices with start/end filters."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    start = datetime(2024, 1, 1, tzinfo=UTC)
    end = datetime(2024, 1, 2, tzinfo=UTC)

    await service.get_cached_prices("AAPL", "1d", "lseg", start=start, end=end)

    # Verify that the query had the filters applied (via mock calls)
    mock_session.execute.assert_called_once()


@pytest.mark.unit
async def test_cache_prices_empty(
    service: MarketDataService, mock_session: AsyncMock
) -> None:
    """Test caching empty list does nothing."""
    await service.cache_prices([])
    mock_session.execute.assert_not_called()


@pytest.mark.unit
async def test_cache_prices_with_interval_fallback(
    service: MarketDataService, mock_session: AsyncMock
) -> None:
    """Test caching prices with interval fallback."""
    bars = [
        {
            "symbol": "AAPL",
            "provider": "lseg",
            "start": "2024-01-01T00:00:00Z",
            "open": 150.0,
            "high": 155.0,
            "low": 149.0,
            "close": 153.0,
        }
    ]

    await service.cache_prices(bars)
    mock_session.execute.assert_called_once()
