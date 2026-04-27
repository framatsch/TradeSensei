"""Unit tests for TimeSeriesService — no database access (all DB calls mocked)."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.timeseries import (
    DailyPnl,
    MonthlyPnl,
    PnlByAssetClass,
    PnlBySymbol,
    ReturnDistribution,
)
from app.services.timeseries_service import TimeSeriesService

# ─── Helpers ──────────────────────────────────────────────────────────────────

_BASE = datetime(2024, 5, 10, 12, 0, 0, tzinfo=UTC)
_PORTFOLIO_ID = uuid.uuid4()


def _dt(day: int, month: int = 5, year: int = 2024) -> datetime:
    """Return a UTC-aware datetime for the given date at noon.

    Args:
        day: Day of month.
        month: Month (default 5 = May).
        year: Year (default 2024).

    Returns:
        A timezone-aware UTC :class:`datetime`.
    """
    return datetime(year, month, day, 12, 0, 0, tzinfo=UTC)


@pytest.fixture()
def service(mock_session: AsyncMock) -> TimeSeriesService:
    """Return a :class:`TimeSeriesService` wired to a mock session."""
    return TimeSeriesService(mock_session)


# ─── get_daily_pnl ────────────────────────────────────────────────────────────


class TestGetDailyPnl:
    """Unit tests for :meth:`TimeSeriesService.get_daily_pnl`."""

    @pytest.mark.unit
    async def test_returns_daily_pnl_with_cumulative(
        self, service: TimeSeriesService
    ) -> None:
        """get_daily_pnl should compute running cumulative PnL across days."""
        from datetime import date

        rows = [
            (date(2024, 5, 10), Decimal("100"), 2),
            (date(2024, 5, 11), Decimal("-50"), 1),
            (date(2024, 5, 12), Decimal("200"), 3),
        ]
        with patch(
            "app.services.timeseries_service.TimeSeriesRepository.get_daily_pnl",
            new_callable=AsyncMock,
            return_value=rows,
        ):
            result = await service.get_daily_pnl(
                user_id=uuid.uuid4(), portfolio_id=_PORTFOLIO_ID
            )

        assert len(result) == 3
        assert all(isinstance(p, DailyPnl) for p in result)
        assert result[0].pnl == Decimal("100")
        assert result[0].cumulative_pnl == Decimal("100")
        assert result[1].pnl == Decimal("-50")
        assert result[1].cumulative_pnl == Decimal("50")
        assert result[2].pnl == Decimal("200")
        assert result[2].cumulative_pnl == Decimal("250")

    @pytest.mark.unit
    async def test_returns_empty_list_when_no_trades(
        self, service: TimeSeriesService
    ) -> None:
        """get_daily_pnl should return an empty list when there are no trades."""
        with patch(
            "app.services.timeseries_service.TimeSeriesRepository.get_daily_pnl",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await service.get_daily_pnl(
                user_id=uuid.uuid4(), portfolio_id=_PORTFOLIO_ID
            )

        assert result == []

    @pytest.mark.unit
    async def test_forwards_filters_to_repository(
        self, service: TimeSeriesService
    ) -> None:
        """get_daily_pnl should forward account_id, from_dt, and to_dt to the repo."""
        account_id = uuid.uuid4()
        from_dt = _dt(1)
        to_dt = _dt(31)

        mock_method = AsyncMock(return_value=[])
        with patch(
            "app.services.timeseries_service.TimeSeriesRepository.get_daily_pnl",
            new=mock_method,
        ):
            await service.get_daily_pnl(
                user_id=uuid.uuid4(),
                portfolio_id=_PORTFOLIO_ID,
                account_id=account_id,
                from_dt=from_dt,
                to_dt=to_dt,
            )

        mock_method.assert_awaited_once()
        kwargs = mock_method.call_args.kwargs
        assert kwargs["account_id"] == account_id
        assert kwargs["from_dt"] == from_dt
        assert kwargs["to_dt"] == to_dt

    @pytest.mark.unit
    async def test_trade_count_preserved(self, service: TimeSeriesService) -> None:
        """DailyPnl.trade_count must reflect the value returned by the repository."""
        from datetime import date

        rows = [(date(2024, 5, 10), Decimal("300"), 5)]
        with patch(
            "app.services.timeseries_service.TimeSeriesRepository.get_daily_pnl",
            new_callable=AsyncMock,
            return_value=rows,
        ):
            result = await service.get_daily_pnl(
                user_id=uuid.uuid4(), portfolio_id=_PORTFOLIO_ID
            )

        assert result[0].trade_count == 5


# ─── get_monthly_pnl ──────────────────────────────────────────────────────────


class TestGetMonthlyPnl:
    """Unit tests for :meth:`TimeSeriesService.get_monthly_pnl`."""

    @pytest.mark.unit
    async def test_aggregates_trades_by_month(self, service: TimeSeriesService) -> None:
        """get_monthly_pnl should group trades by year/month and compute win rate."""
        series = [
            (_dt(5), Decimal("100"), "AAPL"),
            (_dt(10), Decimal("-30"), "AAPL"),
            (_dt(15), Decimal("200"), "MSFT"),
            (_dt(1, month=6), Decimal("50"), "GOOG"),
        ]
        with patch(
            "app.services.timeseries_service.TimeSeriesRepository.get_closed_pnl_series",
            new_callable=AsyncMock,
            return_value=series,
        ):
            result = await service.get_monthly_pnl(
                user_id=uuid.uuid4(), portfolio_id=_PORTFOLIO_ID
            )

        assert len(result) == 2
        assert all(isinstance(m, MonthlyPnl) for m in result)

        may = result[0]
        assert may.year == 2024
        assert may.month == 5
        assert may.pnl == Decimal("270")  # 100 - 30 + 200
        assert may.trade_count == 3
        # 2 winners out of 3 → win_rate ≈ 0.6667
        assert may.win_rate == Decimal(2) / Decimal(3)

        june = result[1]
        assert june.month == 6
        assert june.pnl == Decimal("50")
        assert june.trade_count == 1
        assert june.win_rate == Decimal("1")

    @pytest.mark.unit
    async def test_returns_empty_list_when_no_trades(
        self, service: TimeSeriesService
    ) -> None:
        """get_monthly_pnl should return an empty list when there are no trades."""
        with patch(
            "app.services.timeseries_service.TimeSeriesRepository.get_closed_pnl_series",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await service.get_monthly_pnl(
                user_id=uuid.uuid4(), portfolio_id=_PORTFOLIO_ID
            )

        assert result == []

    @pytest.mark.unit
    async def test_month_win_rate_zero_for_all_losers(
        self, service: TimeSeriesService
    ) -> None:
        """win_rate should be 0.0 when no trade in the month is profitable."""
        series = [
            (_dt(5), Decimal("-100"), "AAPL"),
            (_dt(10), Decimal("-50"), "AAPL"),
        ]
        with patch(
            "app.services.timeseries_service.TimeSeriesRepository.get_closed_pnl_series",
            new_callable=AsyncMock,
            return_value=series,
        ):
            result = await service.get_monthly_pnl(
                user_id=uuid.uuid4(), portfolio_id=_PORTFOLIO_ID
            )

        assert result[0].win_rate == Decimal("0")


# ─── get_pnl_by_symbol ────────────────────────────────────────────────────────


class TestGetPnlBySymbol:
    """Unit tests for :meth:`TimeSeriesService.get_pnl_by_symbol`."""

    @pytest.mark.unit
    async def test_computes_win_rate_and_avg_pnl(
        self, service: TimeSeriesService
    ) -> None:
        """get_pnl_by_symbol should derive win_rate and avg_pnl from repo data."""
        rows = [
            ("AAPL", Decimal("400"), 4, 3),
            ("TSLA", Decimal("-100"), 2, 0),
        ]
        with patch(
            "app.services.timeseries_service.TimeSeriesRepository.get_pnl_by_symbol",
            new_callable=AsyncMock,
            return_value=rows,
        ):
            result = await service.get_pnl_by_symbol(
                user_id=uuid.uuid4(), portfolio_id=_PORTFOLIO_ID
            )

        assert len(result) == 2
        assert all(isinstance(p, PnlBySymbol) for p in result)

        aapl = result[0]
        assert aapl.symbol == "AAPL"
        assert aapl.total_pnl == Decimal("400")
        assert aapl.trade_count == 4
        assert aapl.win_rate == Decimal("3") / Decimal("4")
        assert aapl.avg_pnl == Decimal("400") / Decimal("4")

        tsla = result[1]
        assert tsla.symbol == "TSLA"
        assert tsla.win_rate == Decimal("0")
        assert tsla.avg_pnl == Decimal("-100") / Decimal("2")

    @pytest.mark.unit
    async def test_returns_empty_list_when_no_trades(
        self, service: TimeSeriesService
    ) -> None:
        """get_pnl_by_symbol should return an empty list when there are no trades."""
        with patch(
            "app.services.timeseries_service.TimeSeriesRepository.get_pnl_by_symbol",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await service.get_pnl_by_symbol(
                user_id=uuid.uuid4(), portfolio_id=_PORTFOLIO_ID
            )

        assert result == []


# ─── get_pnl_by_asset_class ───────────────────────────────────────────────────


class TestGetPnlByAssetClass:
    """Unit tests for :meth:`TimeSeriesService.get_pnl_by_asset_class`."""

    @pytest.mark.unit
    async def test_computes_win_rate(self, service: TimeSeriesService) -> None:
        """get_pnl_by_asset_class should compute win_rate from repo data."""
        rows = [
            ("EQUITY", Decimal("1000"), 10, 7),
            ("OPTION", Decimal("-200"), 5, 1),
        ]
        with patch(
            "app.services.timeseries_service.TimeSeriesRepository.get_pnl_by_asset_class",
            new_callable=AsyncMock,
            return_value=rows,
        ):
            result = await service.get_pnl_by_asset_class(
                user_id=uuid.uuid4(), portfolio_id=_PORTFOLIO_ID
            )

        assert len(result) == 2
        assert all(isinstance(p, PnlByAssetClass) for p in result)

        eq = result[0]
        assert eq.asset_class == "EQUITY"
        assert eq.total_pnl == Decimal("1000")
        assert eq.trade_count == 10
        assert eq.win_rate == Decimal("7") / Decimal("10")

        opt = result[1]
        assert opt.win_rate == Decimal("1") / Decimal("5")

    @pytest.mark.unit
    async def test_returns_empty_list_when_no_trades(
        self, service: TimeSeriesService
    ) -> None:
        """get_pnl_by_asset_class should return an empty list when no trades exist."""
        with patch(
            "app.services.timeseries_service.TimeSeriesRepository.get_pnl_by_asset_class",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await service.get_pnl_by_asset_class(
                user_id=uuid.uuid4(), portfolio_id=_PORTFOLIO_ID
            )

        assert result == []


# ─── get_return_distribution ──────────────────────────────────────────────────


class TestGetReturnDistribution:
    """Unit tests for :meth:`TimeSeriesService.get_return_distribution`."""

    @pytest.mark.unit
    async def test_returns_correct_bucket_count(
        self, service: TimeSeriesService
    ) -> None:
        """get_return_distribution should return exactly ``buckets`` entries."""
        series = [(_dt(i + 1), Decimal(str((i - 5) * 100)), "AAPL") for i in range(20)]
        with patch(
            "app.services.timeseries_service.TimeSeriesRepository.get_closed_pnl_series",
            new_callable=AsyncMock,
            return_value=series,
        ):
            result = await service.get_return_distribution(
                user_id=uuid.uuid4(), portfolio_id=_PORTFOLIO_ID, buckets=10
            )

        assert len(result) == 10
        assert all(isinstance(r, ReturnDistribution) for r in result)

    @pytest.mark.unit
    async def test_frequency_sums_to_one(self, service: TimeSeriesService) -> None:
        """Sum of all bucket frequencies must equal 1.0 when trades exist."""
        series = [(_dt(i + 1), Decimal(str(i * 50 - 100)), "AAPL") for i in range(10)]
        with patch(
            "app.services.timeseries_service.TimeSeriesRepository.get_closed_pnl_series",
            new_callable=AsyncMock,
            return_value=series,
        ):
            result = await service.get_return_distribution(
                user_id=uuid.uuid4(), portfolio_id=_PORTFOLIO_ID, buckets=5
            )

        total_freq = sum(r.frequency for r in result)
        assert total_freq == Decimal("1")

    @pytest.mark.unit
    async def test_count_sums_to_total_trades(self, service: TimeSeriesService) -> None:
        """Sum of all bucket counts must equal the total number of trades."""
        n = 15
        series = [
            (_dt(1) + timedelta(days=i), Decimal(str(i * 10 - 70)), "AAPL")
            for i in range(n)
        ]
        with patch(
            "app.services.timeseries_service.TimeSeriesRepository.get_closed_pnl_series",
            new_callable=AsyncMock,
            return_value=series,
        ):
            result = await service.get_return_distribution(
                user_id=uuid.uuid4(), portfolio_id=_PORTFOLIO_ID, buckets=5
            )

        assert sum(r.count for r in result) == n

    @pytest.mark.unit
    async def test_returns_empty_list_when_no_trades(
        self, service: TimeSeriesService
    ) -> None:
        """get_return_distribution should return an empty list when no trades exist."""
        with patch(
            "app.services.timeseries_service.TimeSeriesRepository.get_closed_pnl_series",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await service.get_return_distribution(
                user_id=uuid.uuid4(), portfolio_id=_PORTFOLIO_ID
            )

        assert result == []

    @pytest.mark.unit
    async def test_single_bucket_for_identical_pnl(
        self, service: TimeSeriesService
    ) -> None:
        """When all trades have the same PnL, a single bucket is returned."""
        series = [(_dt(i + 1), Decimal("100"), "AAPL") for i in range(5)]
        with patch(
            "app.services.timeseries_service.TimeSeriesRepository.get_closed_pnl_series",
            new_callable=AsyncMock,
            return_value=series,
        ):
            result = await service.get_return_distribution(
                user_id=uuid.uuid4(), portfolio_id=_PORTFOLIO_ID, buckets=10
            )

        assert len(result) == 1
        assert result[0].count == 5
        assert result[0].frequency == Decimal("1")
        assert result[0].bucket_min == Decimal("100")
        assert result[0].bucket_max == Decimal("100")

    @pytest.mark.unit
    async def test_default_bucket_count(self, service: TimeSeriesService) -> None:
        """Default bucket count should be RETURN_DISTRIBUTION_DEFAULT_BUCKETS."""
        from app.core.constants import RETURN_DISTRIBUTION_DEFAULT_BUCKETS

        series = [
            (_dt(1) + timedelta(days=i), Decimal(str(i * 10)), "AAPL")
            for i in range(50)
        ]
        with patch(
            "app.services.timeseries_service.TimeSeriesRepository.get_closed_pnl_series",
            new_callable=AsyncMock,
            return_value=series,
        ):
            result = await service.get_return_distribution(
                user_id=uuid.uuid4(), portfolio_id=_PORTFOLIO_ID
            )

        assert len(result) == RETURN_DISTRIBUTION_DEFAULT_BUCKETS
