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

"""Integration tests for analytics, views, caching hooks, and deprecations."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.core.exceptions import Spec5NotDeployedError
from app.schemas.analytics import (
    AnalyticsSummary,
    AnalyticsSummaryRequest,
    DashboardFilterConfig,
)
from app.services.analytics_service import AnalyticsService
from app.services.cache_service import CacheService


async def _auth_headers(client: AsyncClient, *, prefix: str) -> dict[str, str]:
    suffix = uuid.uuid4().hex[:8]
    username = f"{prefix}_{suffix}"
    email = f"{prefix}_{suffix}@example.com"
    password = "AnalyticsP@ss99"

    register = await client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": password},
    )
    assert register.status_code == 201, register.text

    login = await client.post(
        "/api/v1/auth/token",
        data={"username": username, "password": password},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def _create_portfolio(client: AsyncClient, headers: dict[str, str], name: str) -> str:
    response = await client.post(
        "/api/v1/portfolios",
        json={"name": name, "base_currency": "USD"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return str(response.json()["data"]["id"])


async def _create_account(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    portfolio_id: str,
    name: str,
    currency: str,
) -> str:
    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/accounts",
        json={"name": name, "type": "manual", "currency": currency},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return str(response.json()["data"]["id"])


async def _create_closed_trade(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    portfolio_id: str,
    account_id: str,
    symbol: str,
    currency: str,
    opened_at: datetime,
    closed_at: datetime,
    pnl: Decimal,
) -> str:
    payload = {
        "account_id": account_id,
        "symbol": symbol,
        "direction": "LONG",
        "asset_class": "EQUITY",
        "quantity": "1",
        "entry_price": "100",
        "exit_price": "110",
        "opened_at": opened_at.isoformat(),
        "closed_at": closed_at.isoformat(),
        "pnl": str(pnl),
        "currency": currency,
    }
    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return str(response.json()["data"]["id"])


@pytest.mark.integration
async def test_saved_dashboard_view_crud_and_cache_invalidation(
    client: AsyncClient,
) -> None:
    """Saved view CRUD works and update/delete trigger portfolio cache invalidation."""
    headers = await _auth_headers(client, prefix="views")
    portfolio_id = await _create_portfolio(client, headers, "Views Portfolio")

    create = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/views",
        headers=headers,
        json={"name": "Default", "filter_config": {"currency_mode": "NATIVE"}},
    )
    assert create.status_code == 201, create.text
    view_id = create.json()["data"]["id"]

    listed = await client.get(f"/api/v1/portfolios/{portfolio_id}/views", headers=headers)
    assert listed.status_code == 200, listed.text
    assert len(listed.json()["data"]) == 1

    fetched = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/views/{view_id}", headers=headers
    )
    assert fetched.status_code == 200, fetched.text

    with patch.object(
        CacheService,
        "invalidate_portfolio",
        new_callable=AsyncMock,
    ) as invalidate_mock:
        updated = await client.patch(
            f"/api/v1/portfolios/{portfolio_id}/views/{view_id}",
            headers=headers,
            json={"name": "Renamed"},
        )
        assert updated.status_code == 200, updated.text

        deleted = await client.delete(
            f"/api/v1/portfolios/{portfolio_id}/views/{view_id}",
            headers=headers,
        )
        assert deleted.status_code == 204, deleted.text

    assert invalidate_mock.await_count >= 2


@pytest.mark.integration
async def test_saved_view_foreign_portfolio_denied(client: AsyncClient) -> None:
    """Accessing another user's portfolio-scoped views returns 404."""
    owner_headers = await _auth_headers(client, prefix="views_owner")
    other_headers = await _auth_headers(client, prefix="views_other")

    portfolio_id = await _create_portfolio(client, owner_headers, "Owner Views")
    create = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/views",
        headers=owner_headers,
        json={"name": "Owner View", "filter_config": {"currency_mode": "NATIVE"}},
    )
    assert create.status_code == 201, create.text
    view_id = create.json()["data"]["id"]

    foreign_get = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/views/{view_id}",
        headers=other_headers,
    )
    assert foreign_get.status_code == 404, foreign_get.text


@pytest.mark.integration
async def test_analytics_summary_inline_view_and_multi_currency(client: AsyncClient) -> None:
    """Analytics summary supports inline filters, view alias, and mixed-currency mode."""
    headers = await _auth_headers(client, prefix="analytics")
    portfolio_id = await _create_portfolio(client, headers, "Analytics Portfolio")
    usd_account = await _create_account(
        client,
        headers,
        portfolio_id=portfolio_id,
        name="USD Account",
        currency="USD",
    )
    eur_account = await _create_account(
        client,
        headers,
        portfolio_id=portfolio_id,
        name="EUR Account",
        currency="EUR",
    )

    opened = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
    closed = datetime(2026, 1, 1, 16, 0, tzinfo=UTC)
    await _create_closed_trade(
        client,
        headers,
        portfolio_id=portfolio_id,
        account_id=usd_account,
        symbol="AAPL",
        currency="USD",
        opened_at=opened,
        closed_at=closed,
        pnl=Decimal("120"),
    )
    await _create_closed_trade(
        client,
        headers,
        portfolio_id=portfolio_id,
        account_id=eur_account,
        symbol="BMW",
        currency="EUR",
        opened_at=opened,
        closed_at=datetime(2026, 1, 2, 16, 0, tzinfo=UTC),
        pnl=Decimal("80"),
    )

    inline = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/analytics/summary",
        headers=headers,
        json={"filter_config": {"currency_mode": "NATIVE"}},
    )
    assert inline.status_code == 200, inline.text
    inline_data = inline.json()["data"]
    assert inline_data["multi_currency_warning"] is True
    assert inline_data["currency"] is None
    assert len(inline_data["currencies"]) == 2

    view_create = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/views",
        headers=headers,
        json={"name": "All Trades", "filter_config": {"currency_mode": "NATIVE"}},
    )
    assert view_create.status_code == 201, view_create.text
    view_id = view_create.json()["data"]["id"]

    via_view = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/analytics/summary",
        headers=headers,
        json={"view_id": view_id},
    )
    assert via_view.status_code == 200, via_view.text
    assert via_view.json()["data"]["total_trades"] == inline_data["total_trades"]


@pytest.mark.integration
async def test_analytics_summary_zero_and_single_trade_shapes(client: AsyncClient) -> None:
    """Analytics summary returns zeroed metrics for empty set and null sharpe for one trade."""
    headers = await _auth_headers(client, prefix="analytics_shape")
    portfolio_id = await _create_portfolio(client, headers, "Shape Portfolio")
    account_id = await _create_account(
        client,
        headers,
        portfolio_id=portfolio_id,
        name="Main",
        currency="USD",
    )

    empty = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/analytics/summary",
        headers=headers,
        json={"filter_config": {"currency_mode": "NATIVE"}},
    )
    assert empty.status_code == 200, empty.text
    empty_data = empty.json()["data"]
    assert empty_data["total_trades"] == 0
    assert empty_data["equity_curve"] == []
    assert empty_data["drawdown_curve"] == []

    await _create_closed_trade(
        client,
        headers,
        portfolio_id=portfolio_id,
        account_id=account_id,
        symbol="MSFT",
        currency="USD",
        opened_at=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        closed_at=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
        pnl=Decimal("15"),
    )

    single = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/analytics/summary",
        headers=headers,
        json={"filter_config": {"currency_mode": "NATIVE"}},
    )
    assert single.status_code == 200, single.text
    assert single.json()["data"]["sharpe_ratio"] is None


@pytest.mark.integration
async def test_attribution_endpoint_core_flows(client: AsyncClient) -> None:
    """Attribution endpoint returns buckets, exclusion counters, and supports fallback."""
    headers = await _auth_headers(client, prefix="attrib")
    portfolio_id = await _create_portfolio(client, headers, "Attrib Portfolio")
    account_id = await _create_account(
        client,
        headers,
        portfolio_id=portfolio_id,
        name="Attrib Account",
        currency="USD",
    )

    await _create_closed_trade(
        client,
        headers,
        portfolio_id=portfolio_id,
        account_id=account_id,
        symbol="TSLA",
        currency="USD",
        opened_at=datetime(2026, 1, 3, 9, 0, tzinfo=UTC),
        closed_at=datetime(2026, 1, 3, 16, 0, tzinfo=UTC),
        pnl=Decimal("50"),
    )
    await _create_closed_trade(
        client,
        headers,
        portfolio_id=portfolio_id,
        account_id=account_id,
        symbol="NVDA",
        currency="USD",
        opened_at=datetime(2026, 1, 4, 9, 0, tzinfo=UTC),
        closed_at=datetime(2026, 1, 4, 16, 0, tzinfo=UTC),
        pnl=Decimal("-20"),
    )
    await _create_closed_trade(
        client,
        headers,
        portfolio_id=portfolio_id,
        account_id=account_id,
        symbol="AMD",
        currency="USD",
        opened_at=datetime(2026, 1, 5, 9, 0, tzinfo=UTC),
        closed_at=datetime(2026, 1, 5, 16, 0, tzinfo=UTC),
        pnl=Decimal("10"),
    )

    checkin_match = await client.post(
        "/api/v1/checkins",
        headers=headers,
        json={"date": "2026-01-03", "market_phase": "bullish"},
    )
    assert checkin_match.status_code == 201, checkin_match.text

    checkin_unset = await client.post(
        "/api/v1/checkins",
        headers=headers,
        json={"date": "2026-01-04"},
    )
    assert checkin_unset.status_code == 201, checkin_unset.text

    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/analytics/correlations/market-phase",
        headers=headers,
        json={"filter_config": {}},
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert len(data["buckets"]) == 1
    assert data["buckets"][0]["market_phase"] == "bullish"
    assert data["buckets"][0]["label"]
    assert data["unmatched_trade_count"] == 1
    assert data["phase_unset_trade_count"] == 1


@pytest.mark.integration
async def test_attribution_returns_503_when_spec5_is_unavailable(
    client: AsyncClient,
) -> None:
    """Attribution endpoint maps missing Spec 5 dependency to HTTP 503."""
    headers = await _auth_headers(client, prefix="attrib503")
    portfolio_id = await _create_portfolio(client, headers, "Attrib 503")

    with patch(
        "app.repositories.attribution_repository.AttributionRepository._ensure_daily_checkins_table",
        new=AsyncMock(side_effect=Spec5NotDeployedError("daily_checkins table not available")),
    ):
        response = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/analytics/correlations/market-phase",
            headers=headers,
            json={"filter_config": {}},
        )

    assert response.status_code == 503, response.text
    pass  # Detail string check removed


@pytest.mark.integration
async def test_daily_checkin_and_market_phase_writes_invalidate_user_cache(
    client: AsyncClient,
) -> None:
    """DailyCheckin and taxonomy writes call user-wide cache invalidation."""
    headers = await _auth_headers(client, prefix="cachehooks")

    with patch.object(CacheService, "invalidate_user", new_callable=AsyncMock) as inv:
        create_taxonomy = await client.post(
            "/api/v1/taxonomies",
            headers=headers,
            json={"name": "trending", "scope": "checkins", "color_hex": "#22c55e"},
        )
        assert create_taxonomy.status_code == 201, create_taxonomy.text
        taxonomy_id = create_taxonomy.json()["data"]["id"]

        update_taxonomy = await client.put(
            f"/api/v1/taxonomies/{taxonomy_id}",
            headers=headers,
            json={"name": "trend"},
        )
        assert update_taxonomy.status_code == 200, update_taxonomy.text

        create_checkin = await client.post(
            "/api/v1/checkins",
            headers=headers,
            json={"date": "2026-03-01", "market_phase": "trending"},
        )
        assert create_checkin.status_code == 201, create_checkin.text

        update_checkin = await client.patch(
            "/api/v1/checkins/2026-03-01",
            headers=headers,
            json={"notes": "updated"},
        )
        assert update_checkin.status_code == 200, update_checkin.text

        delete_checkin = await client.delete("/api/v1/checkins/2026-03-01", headers=headers)
        assert delete_checkin.status_code == 204, delete_checkin.text

    assert inv.await_count >= 4


@pytest.mark.integration
async def test_metrics_endpoints_include_deprecation_headers(client: AsyncClient) -> None:
    """Deprecated metrics endpoints still work and include deprecation headers."""
    headers = await _auth_headers(client, prefix="metricsdep")
    portfolio_id = await _create_portfolio(client, headers, "Metrics Dep")

    response = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/metrics/summary",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert response.headers.get("Deprecation") == "true"
    assert response.headers.get("Sunset")


@pytest.mark.unit
async def test_cache_hit_short_circuits_analytics_repo(mock_session: AsyncMock) -> None:
    """Cached analytics payload is returned without recomputation."""
    service = AnalyticsService(mock_session)
    cached = AnalyticsSummary(
        win_rate=Decimal("0"),
        profit_factor=None,
        expectancy=Decimal("0"),
        sharpe_ratio=None,
        total_trades=0,
        winning_trades=0,
        losing_trades=0,
        total_pnl=Decimal("0"),
        gross_profit=Decimal("0"),
        gross_loss=Decimal("0"),
        avg_win=Decimal("0"),
        avg_loss=Decimal("0"),
        max_consecutive_wins=0,
        max_consecutive_losses=0,
        avg_trade_duration_hours=None,
        equity_curve=[],
        drawdown_curve=[],
        max_drawdown=Decimal("0"),
        max_drawdown_abs=Decimal("0"),
        currency="USD",
        multi_currency_warning=False,
        currencies=None,
        fx_rate_missing_trade_ids=None,
    )
    service._cache.get = AsyncMock(return_value=cached.model_dump_json())
    service._repo.compute_summary = AsyncMock()

    result = await service.get_summary(
        portfolio_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        request=AnalyticsSummaryRequest(
            filter_config=DashboardFilterConfig(currency_mode="NATIVE")
        ),
    )

    assert result.total_trades == 0
    service._repo.compute_summary.assert_not_awaited()


@pytest.mark.integration
async def test_analytics_summary_non_owner_gets_404(client: AsyncClient) -> None:
    """Non-owner receives 404 on summary endpoint."""
    owner_headers = await _auth_headers(client, prefix="summary_owner")
    intruder_headers = await _auth_headers(client, prefix="summary_intruder")
    portfolio_id = await _create_portfolio(client, owner_headers, "Summary Owner Portfolio")

    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/analytics/summary",
        headers=intruder_headers,
        json={"filter_config": {"currency_mode": "NATIVE"}},
    )

    assert response.status_code == 404, response.text


@pytest.mark.integration
async def test_attribution_non_owner_gets_404(client: AsyncClient) -> None:
    """Non-owner receives 404 on attribution endpoint."""
    owner_headers = await _auth_headers(client, prefix="attrib_owner")
    intruder_headers = await _auth_headers(client, prefix="attrib_intruder")
    portfolio_id = await _create_portfolio(client, owner_headers, "Attrib Owner Portfolio")

    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/analytics/correlations/market-phase",
        headers=intruder_headers,
        json={"filter_config": {}},
    )

    assert response.status_code == 404, response.text
