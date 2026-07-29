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

"""Extended unit tests for AnalyticsService — static methods and metrics logic."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.services.analytics_service import AnalyticsService

pytestmark = pytest.mark.asyncio

_USER_ID = uuid.uuid4()
_PORTFOLIO_ID = uuid.uuid4()


# ---------------------------------------------------------------------------
# Helpers to build EquityRow-like dicts
# ---------------------------------------------------------------------------


def _row(pnl: float, dt: date = date(2024, 1, 15), currency: str = "USD") -> dict:
    return {
        "trade_id": uuid.uuid4(),
        "closed_date": dt,
        "pnl": Decimal(str(pnl)),
        "currency": currency,
    }


def _make_service():
    svc = AnalyticsService.__new__(AnalyticsService)
    return svc


# ---------------------------------------------------------------------------
# _compute_streaks
# ---------------------------------------------------------------------------


async def test_compute_streaks_empty_rows():
    max_wins, max_losses = AnalyticsService._compute_streaks([])
    assert max_wins == 0
    assert max_losses == 0


async def test_compute_streaks_all_wins():
    rows = [_row(100), _row(200), _row(50)]
    max_wins, max_losses = AnalyticsService._compute_streaks(rows)
    assert max_wins == 3
    assert max_losses == 0


async def test_compute_streaks_all_losses():
    rows = [_row(-100), _row(-200)]
    max_wins, max_losses = AnalyticsService._compute_streaks(rows)
    assert max_wins == 0
    assert max_losses == 2


async def test_compute_streaks_mixed():
    rows = [_row(100), _row(-50), _row(-30), _row(200), _row(100), _row(100)]
    max_wins, max_losses = AnalyticsService._compute_streaks(rows)
    assert max_wins == 3
    assert max_losses == 2


async def test_compute_streaks_zero_pnl_breaks_streak():
    rows = [_row(100), _row(0), _row(100)]
    max_wins, max_losses = AnalyticsService._compute_streaks(rows)
    assert max_wins == 1  # zero breaks the win streak


# ---------------------------------------------------------------------------
# _compute_sharpe
# ---------------------------------------------------------------------------


async def test_compute_sharpe_returns_none_for_single_row():
    rows = [_row(100)]
    result = AnalyticsService._compute_sharpe(rows)
    assert result is None


async def test_compute_sharpe_returns_none_for_empty():
    result = AnalyticsService._compute_sharpe([])
    assert result is None


async def test_compute_sharpe_returns_none_when_all_same_value():
    # Same PnL every day → zero variance → None
    rows = [_row(100, date(2024, 1, d)) for d in range(1, 11)]
    result = AnalyticsService._compute_sharpe(rows)
    assert result is None


async def test_compute_sharpe_returns_decimal_for_mixed_pnl():
    rows = [
        _row(100, date(2024, 1, 1)),
        _row(-50, date(2024, 1, 2)),
        _row(200, date(2024, 1, 3)),
    ]
    result = AnalyticsService._compute_sharpe(rows)
    assert result is not None
    assert isinstance(result, Decimal)


# ---------------------------------------------------------------------------
# _compute_metrics
# ---------------------------------------------------------------------------


async def test_compute_metrics_all_wins():
    svc = _make_service()
    rows = [_row(100), _row(200)]
    metrics = svc._compute_metrics(rows)
    assert metrics.total_trades == 2
    assert metrics.winning_trades == 2
    assert metrics.losing_trades == 0
    assert metrics.gross_profit == Decimal("300")
    assert metrics.gross_loss == Decimal("0")
    assert metrics.profit_factor is None  # No losses


async def test_compute_metrics_all_losses():
    svc = _make_service()
    rows = [_row(-100), _row(-50)]
    metrics = svc._compute_metrics(rows)
    assert metrics.total_trades == 2
    assert metrics.winning_trades == 0
    assert metrics.losing_trades == 2
    assert metrics.gross_profit == Decimal("0")
    assert metrics.profit_factor is not None  # Has losses but no profit


async def test_compute_metrics_mixed():
    svc = _make_service()
    rows = [_row(100), _row(-50), _row(200), _row(-25)]
    metrics = svc._compute_metrics(rows)
    assert metrics.total_trades == 4
    assert metrics.winning_trades == 2
    assert metrics.losing_trades == 2
    assert metrics.gross_profit == Decimal("300")
    assert metrics.gross_loss == Decimal("-75")
    assert metrics.profit_factor == Decimal("300") / Decimal("75")


async def test_compute_metrics_empty_rows():
    svc = _make_service()
    metrics = svc._compute_metrics([])
    assert metrics.total_trades == 0
    assert metrics.win_rate == Decimal("0")


async def test_compute_metrics_win_rate():
    svc = _make_service()
    rows = [_row(100), _row(100), _row(-50)]
    metrics = svc._compute_metrics(rows)
    assert metrics.win_rate == Decimal("2") / Decimal("3")


# ---------------------------------------------------------------------------
# _build_curves
# ---------------------------------------------------------------------------


async def test_build_curves_empty():
    ec, dc, max_dd, max_dd_abs = AnalyticsService._build_curves([], currency="USD")
    assert ec == []
    assert dc == []
    assert max_dd == Decimal("0")
    assert max_dd_abs == Decimal("0")


async def test_build_curves_single_win():
    rows = [_row(100)]
    ec, dc, max_dd, max_dd_abs = AnalyticsService._build_curves(rows, currency="USD")
    assert len(ec) == 1
    assert ec[0].equity == Decimal("100")
    assert max_dd == Decimal("0")


async def test_build_curves_drawdown_computed():
    rows = [_row(100), _row(-50), _row(200)]
    ec, dc, max_dd, max_dd_abs = AnalyticsService._build_curves(rows, currency="USD")
    # After first row: equity=100, peak=100 → drawdown=0
    # After second row: equity=50, peak=100 → drawdown=-50%
    assert max_dd < Decimal("0")
    assert max_dd_abs < Decimal("0")


# ---------------------------------------------------------------------------
# _downsample_rows
# ---------------------------------------------------------------------------


async def test_downsample_returns_all_when_below_max():

    rows = [_row(i) for i in range(10)]
    result = AnalyticsService._downsample_rows(rows)
    assert len(result) == len(rows)


async def test_downsample_reduces_large_dataset():
    from app.core.constants import EQUITY_CURVE_MAX_POINTS

    rows = [_row(i) for i in range(EQUITY_CURVE_MAX_POINTS + 100)]
    result = AnalyticsService._downsample_rows(rows)
    assert len(result) == EQUITY_CURVE_MAX_POINTS


# ---------------------------------------------------------------------------
# _normalize_rows
# ---------------------------------------------------------------------------


async def test_normalize_rows_skips_rows_with_none_currency():
    svc = _make_service()
    svc._fx = AsyncMock()
    svc._session = AsyncMock()
    rows = [
        {"trade_id": uuid.uuid4(), "closed_date": date(2024, 1, 1), "pnl": Decimal("100"), "currency": None}
    ]
    normalized, missing = await svc._normalize_rows(rows=rows, normalize_to="EUR")
    assert len(normalized) == 0
    assert len(missing) == 1


async def test_normalize_rows_passes_through_matching_currency():
    svc = _make_service()
    svc._fx = AsyncMock()
    svc._session = AsyncMock()
    tid = uuid.uuid4()
    rows = [
        {"trade_id": tid, "closed_date": date(2024, 1, 1), "pnl": Decimal("100"), "currency": "EUR"}
    ]
    normalized, missing = await svc._normalize_rows(rows=rows, normalize_to="EUR")
    assert len(normalized) == 1
    assert normalized[0]["pnl"] == Decimal("100")
    assert len(missing) == 0


async def test_normalize_rows_converts_currency():
    svc = _make_service()
    svc._session = AsyncMock()
    svc._fx = AsyncMock()
    svc._fx.get_by_date = AsyncMock(return_value=Decimal("0.9"))
    svc._fx.get_nearest_within_window = AsyncMock(return_value=None)

    tid = uuid.uuid4()
    rows = [
        {"trade_id": tid, "closed_date": date(2024, 1, 15), "pnl": Decimal("100"), "currency": "USD"}
    ]
    normalized, missing = await svc._normalize_rows(rows=rows, normalize_to="EUR")
    assert len(normalized) == 1
    assert normalized[0]["pnl"] == Decimal("90.0")
    assert len(missing) == 0


async def test_normalize_rows_uses_fallback_rate_when_exact_missing():
    svc = _make_service()
    svc._session = AsyncMock()
    svc._fx = AsyncMock()
    svc._fx.get_by_date = AsyncMock(return_value=None)
    svc._fx.get_nearest_within_window = AsyncMock(return_value=Decimal("0.85"))

    tid = uuid.uuid4()
    rows = [
        {"trade_id": tid, "closed_date": date(2024, 1, 15), "pnl": Decimal("100"), "currency": "USD"}
    ]
    normalized, missing = await svc._normalize_rows(rows=rows, normalize_to="EUR")
    assert len(normalized) == 1
    assert normalized[0]["pnl"] == Decimal("85.0")


async def test_normalize_rows_adds_to_missing_when_no_rate():
    svc = _make_service()
    svc._session = AsyncMock()
    svc._fx = AsyncMock()
    svc._fx.get_by_date = AsyncMock(return_value=None)
    svc._fx.get_nearest_within_window = AsyncMock(return_value=None)

    tid = uuid.uuid4()
    rows = [
        {"trade_id": tid, "closed_date": date(2024, 1, 15), "pnl": Decimal("100"), "currency": "USD"}
    ]
    normalized, missing = await svc._normalize_rows(rows=rows, normalize_to="EUR")
    assert len(normalized) == 0
    assert tid in missing
