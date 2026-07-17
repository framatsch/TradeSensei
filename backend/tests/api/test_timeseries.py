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

"""Integration tests for the /api/v1/timeseries endpoints."""

import uuid
from typing import Any
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.timeseries import _get_service
from app.models.account import Account, AccountType
from app.models.portfolio import Portfolio

pytestmark = pytest.mark.asyncio


async def _make_portfolio_and_account(db_session: AsyncSession, user_id: uuid.UUID) -> tuple[Portfolio, Account]:
    p = Portfolio(user_id=user_id, name="TS Portfolio", base_currency="USD")
    db_session.add(p)
    await db_session.flush()
    await db_session.refresh(p)
    
    a = Account(user_id=user_id, portfolio_id=p.id, name="TS Account", type=AccountType.MANUAL, currency="USD")
    db_session.add(a)
    await db_session.flush()
    await db_session.refresh(a)
    
    return p, a


@pytest.mark.integration
async def test_get_daily_pnl(
    client: AsyncClient,
    primary_user: dict[str, Any],
    db_session: AsyncSession,
):
    portfolio, _ = await _make_portfolio_and_account(db_session, uuid.UUID(primary_user["user_id"]))
    
    response = await client.get(
        f"/api/v1/portfolios/{portfolio.id}/timeseries/daily-pnl",
        headers=primary_user["headers"],
    )
    assert response.status_code == 200
    assert response.json()["data"] == []


@pytest.mark.integration
async def test_get_monthly_pnl(
    client: AsyncClient,
    primary_user: dict[str, Any],
    db_session: AsyncSession,
):
    portfolio, _ = await _make_portfolio_and_account(db_session, uuid.UUID(primary_user["user_id"]))
    
    response = await client.get(
        f"/api/v1/portfolios/{portfolio.id}/timeseries/monthly-pnl",
        headers=primary_user["headers"],
    )
    assert response.status_code == 200
    assert response.json()["data"] == []


@pytest.mark.integration
async def test_get_pnl_by_symbol(
    client: AsyncClient,
    primary_user: dict[str, Any],
    db_session: AsyncSession,
):
    portfolio, _ = await _make_portfolio_and_account(db_session, uuid.UUID(primary_user["user_id"]))
    
    response = await client.get(
        f"/api/v1/portfolios/{portfolio.id}/timeseries/pnl-by-symbol",
        headers=primary_user["headers"],
    )
    assert response.status_code == 200
    assert response.json()["data"] == []


@pytest.mark.integration
async def test_get_pnl_by_asset_class(
    client: AsyncClient,
    primary_user: dict[str, Any],
    db_session: AsyncSession,
):
    portfolio, _ = await _make_portfolio_and_account(db_session, uuid.UUID(primary_user["user_id"]))
    
    response = await client.get(
        f"/api/v1/portfolios/{portfolio.id}/timeseries/pnl-by-asset-class",
        headers=primary_user["headers"],
    )
    assert response.status_code == 200
    assert response.json()["data"] == []


@pytest.mark.integration
async def test_get_return_distribution(
    client: AsyncClient,
    primary_user: dict[str, Any],
    db_session: AsyncSession,
):
    portfolio, _ = await _make_portfolio_and_account(db_session, uuid.UUID(primary_user["user_id"]))
    
    response = await client.get(
        f"/api/v1/portfolios/{portfolio.id}/timeseries/return-distribution",
        headers=primary_user["headers"],
    )
    assert response.status_code == 200
    assert response.json()["data"] == []


@pytest.mark.integration
async def test_get_rolling_winrate(
    client: AsyncClient,
    primary_user: dict[str, Any],
    db_session: AsyncSession,
):
    portfolio, _ = await _make_portfolio_and_account(db_session, uuid.UUID(primary_user["user_id"]))
    
    response = await client.get(
        f"/api/v1/portfolios/{portfolio.id}/timeseries/rolling-winrate",
        headers=primary_user["headers"],
    )
    assert response.status_code == 200
    assert response.json()["data"] == []


@pytest.mark.integration
async def test_get_monthly_winrate(
    client: AsyncClient,
    primary_user: dict[str, Any],
    db_session: AsyncSession,
):
    portfolio, _ = await _make_portfolio_and_account(db_session, uuid.UUID(primary_user["user_id"]))
    
    response = await client.get(
        f"/api/v1/portfolios/{portfolio.id}/timeseries/monthly-winrate",
        headers=primary_user["headers"],
    )
    assert response.status_code == 200
    assert response.json()["data"] == []


@pytest.mark.integration
async def test_timeseries_endpoints_handle_value_error_mocked(
    client: AsyncClient,
    primary_user: dict[str, Any],
    db_session: AsyncSession,
):
    portfolio, _ = await _make_portfolio_and_account(db_session, uuid.UUID(primary_user["user_id"]))
    
    # Create a mock service that raises ValueError
    mock_service = AsyncMock()
    mock_service.get_daily_pnl.side_effect = ValueError("Test Error")
    mock_service.get_monthly_pnl.side_effect = ValueError("Test Error")
    mock_service.get_pnl_by_symbol.side_effect = ValueError("Test Error")
    mock_service.get_pnl_by_asset_class.side_effect = ValueError("Test Error")
    mock_service.get_return_distribution.side_effect = ValueError("Test Error")
    mock_service.get_rolling_winrate.side_effect = ValueError("Test Error")
    mock_service.get_monthly_winrate.side_effect = ValueError("Test Error")
    
    # Override the dependency
    from app.main import app
    app.dependency_overrides[_get_service] = lambda: mock_service
    
    endpoints = [
        "daily-pnl",
        "monthly-pnl",
        "pnl-by-symbol",
        "pnl-by-asset-class",
        "return-distribution",
        "rolling-winrate",
        "monthly-winrate"
    ]
    
    for endpoint in endpoints:
        response = await client.get(
            f"/api/v1/portfolios/{portfolio.id}/timeseries/{endpoint}",
            headers=primary_user["headers"],
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Test Error"
        
    app.dependency_overrides.clear()
