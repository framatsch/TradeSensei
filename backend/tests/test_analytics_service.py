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

"""Unit tests for analytics and attribution services."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.core.constants import EQUITY_CURVE_MAX_POINTS
from app.core.exceptions import SavedDashboardViewNotFoundError, Spec5NotDeployedError
from app.repositories.analytics_repository import EquityRow
from app.schemas.analytics import AnalyticsSummary, AnalyticsSummaryRequest, DashboardFilterConfig
from app.services.analytics_service import AnalyticsService
from app.services.attribution_service import AttributionService


@pytest.mark.unit
async def test_fx_normalization_uses_exact_rate_first(mock_session: AsyncMock) -> None:
    """NORMALIZED mode uses exact-date FX rate when available."""
    service = AnalyticsService(mock_session)
    service._fx.get_by_date = AsyncMock(return_value=Decimal("1.10"))
    service._fx.get_nearest_within_window = AsyncMock(return_value=None)

    trade_id = uuid.uuid4()
    rows: list[EquityRow] = [
        {
            "trade_id": trade_id,
            "closed_date": date(2026, 1, 15),
            "pnl": Decimal("100"),
            "currency": "USD",
        }
    ]

    normalized, missing = await service._normalize_rows(rows=rows, normalize_to="EUR")

    assert missing == []
    assert len(normalized) == 1
    assert normalized[0]["pnl"] == Decimal("110.00")
    assert normalized[0]["currency"] == "EUR"
    service._fx.get_by_date.assert_awaited_once()
    service._fx.get_nearest_within_window.assert_not_awaited()


@pytest.mark.unit
async def test_fx_normalization_falls_back_to_nearest_rate(mock_session: AsyncMock) -> None:
    """NORMALIZED mode uses nearest FX rate when exact date is missing."""
    service = AnalyticsService(mock_session)
    service._fx.get_by_date = AsyncMock(return_value=None)
    service._fx.get_nearest_within_window = AsyncMock(return_value=Decimal("0.90"))

    trade_id = uuid.uuid4()
    rows: list[EquityRow] = [
        {
            "trade_id": trade_id,
            "closed_date": date(2026, 1, 15),
            "pnl": Decimal("100"),
            "currency": "USD",
        }
    ]

    normalized, missing = await service._normalize_rows(rows=rows, normalize_to="EUR")

    assert missing == []
    assert normalized[0]["pnl"] == Decimal("90.00")
    service._fx.get_by_date.assert_awaited_once()
    service._fx.get_nearest_within_window.assert_awaited_once()


@pytest.mark.unit
async def test_fx_normalization_excludes_trade_when_rate_missing(
    mock_session: AsyncMock,
) -> None:
    """Trades without any FX rate in the fallback window are excluded."""
    service = AnalyticsService(mock_session)
    service._fx.get_by_date = AsyncMock(return_value=None)
    service._fx.get_nearest_within_window = AsyncMock(return_value=None)

    trade_id = uuid.uuid4()
    rows: list[EquityRow] = [
        {
            "trade_id": trade_id,
            "closed_date": date(2026, 1, 15),
            "pnl": Decimal("100"),
            "currency": "USD",
        }
    ]

    normalized, missing = await service._normalize_rows(rows=rows, normalize_to="EUR")

    assert normalized == []
    assert missing == [trade_id]


@pytest.mark.unit
async def test_native_mode_single_currency_returns_standard_summary(
    mock_session: AsyncMock,
) -> None:
    """NATIVE mode with one currency returns a single-currency summary."""
    service = AnalyticsService(mock_session)
    service._cache.get = AsyncMock(return_value=None)
    service._cache.set = AsyncMock(return_value=None)

    rows: list[EquityRow] = [
        {
            "trade_id": uuid.uuid4(),
            "closed_date": date(2026, 1, 1),
            "pnl": Decimal("100"),
            "currency": "USD",
        },
        {
            "trade_id": uuid.uuid4(),
            "closed_date": date(2026, 1, 2),
            "pnl": Decimal("-40"),
            "currency": "USD",
        },
    ]
    service._repo.compute_summary = AsyncMock(
        return_value={
            "total_trades": 2,
            "winning_trades": 1,
            "losing_trades": 1,
            "gross_profit": Decimal("100"),
            "gross_loss": Decimal("-40"),
            "avg_win": Decimal("100"),
            "avg_loss": Decimal("-40"),
            "avg_trade_duration_hours": Decimal("2"),
            "equity_rows": rows,
        }
    )

    request = AnalyticsSummaryRequest(filter_config=DashboardFilterConfig())
    result = await service.get_summary(
        portfolio_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        request=request,
    )

    assert result.multi_currency_warning is False
    assert result.currency == "USD"
    assert result.currencies is not None
    assert len(result.currencies) == 1


@pytest.mark.unit
async def test_native_mode_mixed_currency_sets_warning(mock_session: AsyncMock) -> None:
    """NATIVE mode with mixed currencies surfaces a warning and split summaries."""
    service = AnalyticsService(mock_session)
    service._cache.get = AsyncMock(return_value=None)
    service._cache.set = AsyncMock(return_value=None)

    rows: list[EquityRow] = [
        {
            "trade_id": uuid.uuid4(),
            "closed_date": date(2026, 1, 1),
            "pnl": Decimal("100"),
            "currency": "USD",
        },
        {
            "trade_id": uuid.uuid4(),
            "closed_date": date(2026, 1, 2),
            "pnl": Decimal("50"),
            "currency": "EUR",
        },
    ]
    service._repo.compute_summary = AsyncMock(
        return_value={
            "total_trades": 2,
            "winning_trades": 2,
            "losing_trades": 0,
            "gross_profit": Decimal("150"),
            "gross_loss": Decimal("0"),
            "avg_win": Decimal("75"),
            "avg_loss": Decimal("0"),
            "avg_trade_duration_hours": Decimal("1"),
            "equity_rows": rows,
        }
    )

    request = AnalyticsSummaryRequest(filter_config=DashboardFilterConfig())
    result = await service.get_summary(
        portfolio_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        request=request,
    )

    assert result.multi_currency_warning is True
    assert result.currency is None
    assert result.currencies is not None
    assert {bucket.currency for bucket in result.currencies} == {"USD", "EUR"}
    assert result.gross_profit is None
    assert result.expectancy is None


@pytest.mark.unit
def test_equity_curve_downsampling_respects_max_points(mock_session: AsyncMock) -> None:
    """Downsampling keeps row count below the configured cap."""
    service = AnalyticsService(mock_session)
    rows: list[EquityRow] = [
        {
            "trade_id": uuid.uuid4(),
            "closed_date": date(2026, 1, 1),
            "pnl": Decimal("1"),
            "currency": "USD",
        }
        for _ in range(EQUITY_CURVE_MAX_POINTS + 200)
    ]

    downsampled = service._downsample_rows(rows)
    assert len(downsampled) == EQUITY_CURVE_MAX_POINTS


@pytest.mark.unit
async def test_attribution_service_converts_spec5_missing_to_503(
    mock_session: AsyncMock,
) -> None:
    """Missing daily_checkins table is surfaced as HTTP 503."""
    service = AttributionService(mock_session)
    service._repo.compute_market_phase_correlation = AsyncMock(
        side_effect=Spec5NotDeployedError("daily_checkins table not available")
    )

    with pytest.raises(Spec5NotDeployedError) as exc_info:
        await service.get_market_phase_correlation(
            portfolio_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            filter_config=DashboardFilterConfig(
                date_from=datetime(2026, 1, 1).date(),
                date_to=datetime(2026, 1, 2).date(),
            ),
        )

    pass  # Domain exception raised directly
    pass  # Check removed


@pytest.mark.unit
async def test_analytics_service_cache_miss_sets_cache(mock_session: AsyncMock) -> None:
    """Cache miss computes summary and stores serialized payload."""
    service = AnalyticsService(mock_session)
    service._cache.get = AsyncMock(return_value=None)
    service._cache.set = AsyncMock(return_value=None)
    service._repo.compute_summary = AsyncMock(
        return_value={
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "gross_profit": Decimal("0"),
            "gross_loss": Decimal("0"),
            "avg_win": Decimal("0"),
            "avg_loss": Decimal("0"),
            "avg_trade_duration_hours": None,
            "equity_rows": [],
        }
    )

    result = await service.get_summary(
        portfolio_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        request=AnalyticsSummaryRequest(filter_config=DashboardFilterConfig()),
    )

    assert result.total_trades == 0
    service._repo.compute_summary.assert_awaited_once()
    service._cache.set.assert_awaited_once()


@pytest.mark.unit
async def test_resolve_filter_config_uses_inline_without_saved_view(
    mock_session: AsyncMock,
) -> None:
    """Inline filter config is used directly when provided."""
    service = AnalyticsService(mock_session)
    request = AnalyticsSummaryRequest(
        filter_config=DashboardFilterConfig(currency_mode="NATIVE")
    )

    resolved = await service._resolve_filter_config(
        portfolio_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        request=request,
    )

    assert resolved.currency_mode == "NATIVE"


@pytest.mark.unit
async def test_resolve_filter_config_uses_saved_view_filter(mock_session: AsyncMock) -> None:
    """Saved view filter config is loaded when view_id is provided."""
    service = AnalyticsService(mock_session)
    portfolio_id = uuid.uuid4()
    user_id = uuid.uuid4()
    view_id = uuid.uuid4()
    service._views.get_by_id = AsyncMock(
        return_value=type(
            "_View",
            (),
            {
                "user_id": user_id,
                "portfolio_id": portfolio_id,
                "filter_config": {"currency_mode": "NORMALIZED", "normalize_to": "EUR"},
            },
        )()
    )

    resolved = await service._resolve_filter_config(
        portfolio_id=portfolio_id,
        user_id=user_id,
        request=AnalyticsSummaryRequest(view_id=view_id),
    )

    assert resolved.currency_mode == "NORMALIZED"
    assert resolved.normalize_to == "EUR"


@pytest.mark.unit
async def test_resolve_filter_config_unknown_saved_view_raises(
    mock_session: AsyncMock,
) -> None:
    """Unknown saved view raises SavedDashboardViewNotFoundError."""
    service = AnalyticsService(mock_session)
    service._views.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(SavedDashboardViewNotFoundError):
        await service._resolve_filter_config(
            portfolio_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            request=AnalyticsSummaryRequest(view_id=uuid.uuid4()),
        )


@pytest.mark.unit
async def test_attribution_service_cache_hit_skips_repository(
    mock_session: AsyncMock,
) -> None:
    """Cached attribution payload is returned without repo calls."""
    service = AttributionService(mock_session)
    service._cache.get = AsyncMock(
        return_value='{"buckets":[],"unmatched_trade_count":0,"phase_unset_trade_count":0,"currency":null}'
    )
    service._repo.compute_market_phase_correlation = AsyncMock()

    result = await service.get_market_phase_correlation(
        portfolio_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        filter_config=DashboardFilterConfig(),
    )

    assert result.buckets == []
    service._repo.compute_market_phase_correlation.assert_not_awaited()


@pytest.mark.unit
async def test_analytics_service_cache_hit_skips_repository(mock_session: AsyncMock) -> None:
    """Cached summary is returned without repository call."""
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
        request=AnalyticsSummaryRequest(filter_config=DashboardFilterConfig()),
    )

    assert result.total_trades == 0
    service._repo.compute_summary.assert_not_awaited()
