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

from typing import Any
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.api.v1.market_data import _get_service
from app.main import app

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_market_data_service():
    mock = AsyncMock()
    return mock


@pytest.fixture
def override_market_data_dependency(mock_market_data_service):
    app.dependency_overrides[_get_service] = lambda: mock_market_data_service
    yield mock_market_data_service
    app.dependency_overrides.clear()


async def test_get_price_history_force_refresh(
    client: AsyncClient, primary_user: dict[str, Any], override_market_data_dependency
):
    # Mock upstream response slightly
    override_market_data_dependency.format_bars.return_value = []

    # When force_refresh=true
    await client.get(
        "/api/v1/market-data/prices/AAPL/history?force_refresh=true",
        headers=primary_user["headers"]
    )
    
    # Assert get_cached_prices was NOT called
    override_market_data_dependency.get_cached_prices.assert_not_called()


async def test_clear_cache(
    client: AsyncClient, primary_user: dict[str, Any], override_market_data_dependency
):
    response = await client.delete(
        "/api/v1/market-data/cache",
        headers=primary_user["headers"]
    )

    assert response.status_code == 204
    # Ensure clear_all_cache was called without arguments
    override_market_data_dependency.clear_all_cache.assert_called_once_with()
