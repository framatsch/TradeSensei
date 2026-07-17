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

import uuid
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.api.v1.analytics import (
    _get_analytics_service,
    _get_attribution_service,
    _get_metadata_correlation_service,
)
from app.core.dependencies import require_portfolio_owner
from app.core.deps import get_session_with_rls
from app.core.exceptions import Spec5NotDeployedError
from app.main import app
from app.models.portfolio import Portfolio
from app.models.saved_dashboard_view import SavedDashboardView
from app.schemas.analytics import (
    AnalyticsSummary,
    AttributionResponse,
    MetadataCorrelationResponse,
)

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_analytics_service():
    return AsyncMock()


@pytest.fixture
def mock_attribution_service():
    return AsyncMock()


@pytest.fixture
def mock_metadata_service():
    return AsyncMock()


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def override_analytics_deps(
    mock_analytics_service,
    mock_attribution_service,
    mock_metadata_service,
    mock_session,
):
    app.dependency_overrides[_get_analytics_service] = lambda: mock_analytics_service
    app.dependency_overrides[_get_attribution_service] = lambda: mock_attribution_service
    app.dependency_overrides[_get_metadata_correlation_service] = lambda: mock_metadata_service
    app.dependency_overrides[get_session_with_rls] = lambda: mock_session
    app.dependency_overrides[require_portfolio_owner] = lambda: None
    yield mock_analytics_service, mock_attribution_service, mock_metadata_service, mock_session
    app.dependency_overrides.clear()


@patch("app.api.v1.analytics.SavedDashboardViewRepository")
async def test_get_metadata_correlation(
    mock_repo_class,
    client: AsyncClient,
    primary_user: dict[str, Any],
    override_analytics_deps,
):
    _, _, mock_metadata, _ = override_analytics_deps
    mock_repo_instance = mock_repo_class.return_value
    
    mock_metadata.get_correlation.return_value = MetadataCorrelationResponse(
        x_axis={"id": "x", "name": "X", "type": "trade_taxonomy"},
        y_axis={"id": "y", "name": "Y", "type": "trade_taxonomy"},
        cells=[],
        kpis={"win_rate": 0, "net_pnl": "0", "total_trades_count": 0, "max_drawdown_pct": "0.00", "matched_count": 0},
        data_points=[],
        x_axis_data_type="trade_taxonomy",
        y_axis_data_type="trade_taxonomy",
        x_axis_name="X",
        y_axis_name="Y"
    )

    portfolio_id = str(uuid.uuid4())
    
    # Test without view_id
    res = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/analytics/correlations/metadata",
        headers=primary_user["headers"],
        json={
            "x_axis_type": "trade_taxonomy",
            "x_axis_id": str(uuid.uuid4()),
            "y_axis_type": "trade_taxonomy",
            "y_axis_id": str(uuid.uuid4()), "filter_config": {},
        },
    )
    assert res.status_code == 200, res.text

    # Test with view_id
    view_id = str(uuid.uuid4())
    mock_repo_instance.get_by_id = AsyncMock(return_value=SavedDashboardView(
        id=uuid.UUID(view_id),
        user_id=uuid.UUID(primary_user["user_id"]),
        portfolio_id=uuid.UUID(portfolio_id),
        filter_config={},
    ))
    
    res2 = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/analytics/correlations/metadata",
        headers=primary_user["headers"],
        json={
            "x_axis_type": "trade_taxonomy",
            "x_axis_id": str(uuid.uuid4()),
            "y_axis_type": "trade_taxonomy",
            "y_axis_id": str(uuid.uuid4()),
            "view_id": view_id,
        },
    )
    assert res2.status_code == 200

    # Test with invalid view
    mock_repo_instance.get_by_id = AsyncMock(return_value=None)
    res3 = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/analytics/correlations/metadata",
        headers=primary_user["headers"],
        json={
            "x_axis_type": "trade_taxonomy",
            "x_axis_id": str(uuid.uuid4()),
            "y_axis_type": "trade_taxonomy",
            "y_axis_id": str(uuid.uuid4()),
            "view_id": view_id,
        },
    )
    assert res3.status_code == 404


async def test_get_analytics_summary(
    client: AsyncClient, primary_user: dict[str, Any], override_analytics_deps
):
    mock_analytics, _, _, _ = override_analytics_deps
    
    mock_analytics.get_summary.return_value = AnalyticsSummary(
        total_trades=0,
        win_rate="0",
        profit_factor="0",
        expectancy="0",
        average_rr="0",
        average_win="0",
        average_loss="0",
        net_pnl="0",
        largest_win="0",
        largest_loss="0",
        max_drawdown="0",
        sharpe_ratio="0",
        winning_trades=0,
        losing_trades=0,
        total_pnl="0",
        gross_profit="0",
        gross_loss="0",
        avg_win="0",
        avg_loss="0",
        max_consecutive_wins=0,
        max_consecutive_losses=0,
        avg_trade_duration_hours="0",
        equity_curve=[],
        drawdown_curve=[],
        max_drawdown_abs="0",
        currency="USD"
    )
    
    portfolio_id = str(uuid.uuid4())
    
    res = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/analytics/summary",
        headers=primary_user["headers"],
        json={"filter_config": {}},
    )
    assert res.status_code == 200, res.text


@patch("app.api.v1.analytics.PortfolioRepository")
@patch("app.api.v1.analytics.SavedDashboardViewRepository")
async def test_get_market_phase_correlation(
    mock_view_repo,
    mock_portfolio_repo,
    client: AsyncClient,
    primary_user: dict[str, Any],
    override_analytics_deps,
):
    _, mock_attribution, _, _ = override_analytics_deps
    
    mock_portfolio_instance = mock_portfolio_repo.return_value
    mock_view_instance = mock_view_repo.return_value
    
    portfolio_id = str(uuid.uuid4())
    mock_portfolio_instance.get_by_id = AsyncMock(return_value=Portfolio(
        id=uuid.UUID(portfolio_id),
        user_id=uuid.UUID(primary_user["user_id"]),
    ))
    
    mock_attribution.get_market_phase_correlation.return_value = AttributionResponse(
        items=[],
        excluded_outliers=0,
        excluded_missing_data=0,
        buckets=[],
        unmatched_trade_count=0,
        phase_unset_trade_count=0,
        currency="USD",
    )
    
    res = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/analytics/correlations/market-phase",
        headers=primary_user["headers"],
        json={"filter_config": {}},
    )
    assert res.status_code == 200, res.text
    
    # Portfolio not found
    mock_portfolio_instance.get_by_id = AsyncMock(return_value=None)
    res2 = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/analytics/correlations/market-phase",
        headers=primary_user["headers"],
        json={"filter_config": {}},
    )
    assert res2.status_code == 404
    
    # Valid view
    mock_portfolio_instance.get_by_id = AsyncMock(return_value=Portfolio(
        id=uuid.UUID(portfolio_id),
        user_id=uuid.UUID(primary_user["user_id"]),
    ))
    view_id = str(uuid.uuid4())
    mock_view_instance.get_by_id = AsyncMock(return_value=SavedDashboardView(
        id=uuid.UUID(view_id),
        user_id=uuid.UUID(primary_user["user_id"]),
        portfolio_id=uuid.UUID(portfolio_id),
        filter_config={},
    ))
    res3 = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/analytics/correlations/market-phase",
        headers=primary_user["headers"],
        json={"view_id": view_id},
    )
    assert res3.status_code == 200
    
    # Invalid view
    mock_view_instance.get_by_id = AsyncMock(return_value=None)
    res4 = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/analytics/correlations/market-phase",
        headers=primary_user["headers"],
        json={"view_id": view_id},
    )
    assert res4.status_code == 404
    
    # Spec5 error
    mock_attribution.get_market_phase_correlation.side_effect = Spec5NotDeployedError()
    mock_view_instance.get_by_id.return_value = SavedDashboardView(
        id=uuid.UUID(view_id),
        user_id=uuid.UUID(primary_user["user_id"]),
        portfolio_id=uuid.UUID(portfolio_id),
        filter_config={},
    )
    res5 = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/analytics/correlations/market-phase",
        headers=primary_user["headers"],
        json={"view_id": view_id},
    )
    assert res5.status_code == 503


async def test_get_analytics_return_distribution(
    client: AsyncClient, primary_user: dict[str, Any], override_analytics_deps
):
    mock_analytics, _, _, _ = override_analytics_deps
    
    mock_analytics.get_return_distribution.return_value = []
    
    portfolio_id = str(uuid.uuid4())
    res = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/analytics/return-distribution?buckets=10",
        headers=primary_user["headers"],
        json={"filter_config": {}},
    )
    assert res.status_code == 200, res.text
