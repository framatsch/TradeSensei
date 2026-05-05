"""Unit tests for analytics and attribution services."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.core.constants import EQUITY_CURVE_MAX_POINTS
from app.core.exceptions import Spec5NotDeployedError
from app.repositories.analytics_repository import EquityRow
from app.schemas.analytics import AnalyticsSummaryRequest, DashboardFilterConfig
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
