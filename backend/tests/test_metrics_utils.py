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

"""Unit tests for the pure metrics utility functions in ``app/utils/metrics.py``.

All tests are pure Python — no database access.
"""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.models.trade import AssetClass, Direction
from app.schemas.metrics import EquityCurvePoint
from app.schemas.trade import TradeRead
from app.utils.metrics import (
    compute_consecutive_runs,
    compute_drawdown_curve,
    compute_equity_curve,
    compute_sharpe_ratio,
    compute_trade_metrics,
)

# ─── Helpers ──────────────────────────────────────────────────────────────────

_NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)


def _make_trade_read(
    pnl: Decimal | None = None,
    opened_at: datetime | None = None,
    closed_at: datetime | None = None,
) -> TradeRead:
    """Build a minimal :class:`TradeRead` for testing.

    Args:
        pnl: PnL value (``None`` means the trade is still open).
        opened_at: Open timestamp. Defaults to ``_NOW``.
        closed_at: Close timestamp. Defaults to ``_NOW + 1 hour`` when
            ``pnl`` is set, else ``None``.

    Returns:
        A :class:`TradeRead` with sensible defaults.
    """
    if opened_at is None:
        opened_at = _NOW
    if closed_at is None and pnl is not None:
        closed_at = opened_at + timedelta(hours=1)
    return TradeRead(
        id=uuid.uuid4(),
        symbol="AAPL",
        direction=Direction.LONG,
        asset_class=AssetClass.EQUITY,
        quantity=Decimal("10"),
        entry_price=Decimal("100"),
        exit_price=Decimal("110") if pnl is not None else None,
        stop_loss=None,
        take_profit=None,
        opened_at=opened_at,
        closed_at=closed_at,
        pnl=pnl,
        commission=Decimal("0"),
        journal=None,
        created_at=opened_at,
        updated_at=opened_at,
    )


def _make_equity_point(
    equity: Decimal,
    pnl: Decimal,
    offset_hours: int = 0,
) -> EquityCurvePoint:
    """Return a minimal :class:`EquityCurvePoint`.

    Args:
        equity: Cumulative equity value.
        pnl: PnL at this point.
        offset_hours: Hour offset from ``_NOW``.

    Returns:
        An :class:`EquityCurvePoint`.
    """
    return EquityCurvePoint(
        timestamp=_NOW + timedelta(hours=offset_hours),
        equity=equity,
        pnl=pnl,
    )


# ─── compute_consecutive_runs ─────────────────────────────────────────────────


class TestComputeConsecutiveRuns:
    """Tests for :func:`compute_consecutive_runs`."""

    @pytest.mark.unit
    def test_empty_series(self) -> None:
        """Should return (0, 0) for an empty series."""
        assert compute_consecutive_runs([]) == (0, 0)

    @pytest.mark.unit
    def test_all_wins(self) -> None:
        """Should correctly count all wins."""
        series = [Decimal("100")] * 5
        assert compute_consecutive_runs(series) == (5, 0)

    @pytest.mark.unit
    def test_all_losses(self) -> None:
        """Should correctly count all losses."""
        series = [Decimal("-50")] * 3
        assert compute_consecutive_runs(series) == (0, 3)

    @pytest.mark.unit
    def test_mixed_series(self) -> None:
        """Should return (3, 2) for a mixed win/loss series."""
        series = [
            Decimal("10"),
            Decimal("20"),
            Decimal("30"),
            Decimal("-10"),
            Decimal("-5"),
            Decimal("5"),
        ]
        assert compute_consecutive_runs(series) == (3, 2)

    @pytest.mark.unit
    def test_breakeven_resets_streak(self) -> None:
        """A breakeven trade should reset both streaks."""
        series = [
            Decimal("10"),
            Decimal("10"),
            Decimal("0"),  # resets wins
            Decimal("5"),
        ]
        wins, losses = compute_consecutive_runs(series)
        assert wins == 2
        assert losses == 0

    @pytest.mark.unit
    def test_alternating_wins_losses(self) -> None:
        """Single alternating wins/losses should give max of 1 each."""
        series = [Decimal("10"), Decimal("-5"), Decimal("10"), Decimal("-5")]
        assert compute_consecutive_runs(series) == (1, 1)


# ─── compute_trade_metrics ────────────────────────────────────────────────────


class TestComputeTradeMetrics:
    """Tests for :func:`compute_trade_metrics`."""

    @pytest.mark.unit
    def test_empty_list(self) -> None:
        """Should return a zero-value TradeMetrics for an empty list."""
        result = compute_trade_metrics([])
        assert result.total_trades == 0
        assert result.win_rate == Decimal("0")
        assert result.profit_factor is None
        assert result.sharpe_ratio is None

    @pytest.mark.unit
    def test_open_trades_excluded(self) -> None:
        """Trades without PnL (still open) must be excluded."""
        trades = [
            _make_trade_read(pnl=None),  # open — excluded
            _make_trade_read(pnl=Decimal("100")),
        ]
        result = compute_trade_metrics(trades)
        assert result.total_trades == 1

    @pytest.mark.unit
    def test_basic_win_rate(self) -> None:
        """Win rate and loss rate should sum to 1.0 (when no breakevens)."""
        trades = [
            _make_trade_read(pnl=Decimal("100")),
            _make_trade_read(pnl=Decimal("200")),
            _make_trade_read(pnl=Decimal("-50")),
        ]
        result = compute_trade_metrics(trades)
        assert result.total_trades == 3
        assert result.winning_trades == 2
        assert result.losing_trades == 1
        assert result.win_rate + result.loss_rate == Decimal("1")

    @pytest.mark.unit
    def test_gross_profit_and_loss(self) -> None:
        """gross_profit should be positive; gross_loss should be negative."""
        trades = [
            _make_trade_read(pnl=Decimal("100")),
            _make_trade_read(pnl=Decimal("-40")),
            _make_trade_read(pnl=Decimal("60")),
        ]
        result = compute_trade_metrics(trades)
        assert result.gross_profit == Decimal("160")
        assert result.gross_loss == Decimal("-40")
        assert result.total_pnl == Decimal("120")

    @pytest.mark.unit
    def test_profit_factor(self) -> None:
        """Profit factor should equal gross_profit / abs(gross_loss)."""
        trades = [
            _make_trade_read(pnl=Decimal("200")),
            _make_trade_read(pnl=Decimal("-100")),
        ]
        result = compute_trade_metrics(trades)
        assert result.profit_factor == Decimal("2")

    @pytest.mark.unit
    def test_profit_factor_none_when_no_losses(self) -> None:
        """Profit factor should be None when there are no losing trades."""
        trades = [
            _make_trade_read(pnl=Decimal("100")),
            _make_trade_read(pnl=Decimal("200")),
        ]
        result = compute_trade_metrics(trades)
        assert result.profit_factor is None

    @pytest.mark.unit
    def test_expectancy_formula(self) -> None:
        """Expectancy = win_rate * avg_win + loss_rate * avg_loss."""
        trades = [
            _make_trade_read(pnl=Decimal("100")),
            _make_trade_read(pnl=Decimal("-50")),
        ]
        result = compute_trade_metrics(trades)
        expected = result.win_rate * result.avg_win + result.loss_rate * result.avg_loss
        assert result.expectancy == expected

    @pytest.mark.unit
    def test_breakeven_trades_counted(self) -> None:
        """Breakeven trades should increment breakeven_trades counter."""
        trades = [
            _make_trade_read(pnl=Decimal("100")),
            _make_trade_read(pnl=Decimal("0")),
            _make_trade_read(pnl=Decimal("-30")),
        ]
        result = compute_trade_metrics(trades)
        assert result.breakeven_trades == 1

    @pytest.mark.unit
    def test_avg_trade_duration(self) -> None:
        """avg_trade_duration_seconds should equal the mean duration."""
        base = _NOW
        t1 = _make_trade_read(
            pnl=Decimal("10"),
            opened_at=base,
            closed_at=base + timedelta(hours=2),
        )
        t2 = _make_trade_read(
            pnl=Decimal("20"),
            opened_at=base,
            closed_at=base + timedelta(hours=4),
        )
        result = compute_trade_metrics([t1, t2])
        # average of 2 h and 4 h = 3 h = 10800 s
        assert result.avg_trade_duration_seconds == pytest.approx(10800.0)

    @pytest.mark.unit
    def test_avg_trade_duration_none_when_no_closed(self) -> None:
        """avg_trade_duration_seconds should be None when closed_at is missing."""
        # Construct a trade with pnl set but closed_at = None explicitly.
        trade2 = TradeRead(
            id=uuid.uuid4(),
            symbol="AAPL",
            direction=Direction.LONG,
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("10"),
            entry_price=Decimal("100"),
            exit_price=Decimal("110"),
            stop_loss=None,
            take_profit=None,
            opened_at=_NOW,
            closed_at=None,  # no closed_at
            pnl=Decimal("10"),
            commission=Decimal("0"),
            journal=None,
            created_at=_NOW,
            updated_at=_NOW,
        )
        result = compute_trade_metrics([trade2])
        assert result.avg_trade_duration_seconds is None


# ─── compute_equity_curve ─────────────────────────────────────────────────────


class TestComputeEquityCurve:
    """Tests for :func:`compute_equity_curve`."""

    @pytest.mark.unit
    def test_empty_list(self) -> None:
        """Should return an empty list for no trades."""
        assert compute_equity_curve([]) == []

    @pytest.mark.unit
    def test_open_trades_excluded(self) -> None:
        """Trades without PnL must not appear in the equity curve."""
        trades = [
            _make_trade_read(pnl=None),
            _make_trade_read(pnl=Decimal("100")),
        ]
        result = compute_equity_curve(trades)
        assert len(result) == 1

    @pytest.mark.unit
    def test_cumulative_equity(self) -> None:
        """Equity should be cumulative (starting_capital + running PnL sum)."""
        base = _NOW
        trades = [
            _make_trade_read(
                pnl=Decimal("100"),
                opened_at=base,
                closed_at=base + timedelta(hours=1),
            ),
            _make_trade_read(
                pnl=Decimal("200"),
                opened_at=base,
                closed_at=base + timedelta(hours=2),
            ),
            _make_trade_read(
                pnl=Decimal("-50"),
                opened_at=base,
                closed_at=base + timedelta(hours=3),
            ),
        ]
        result = compute_equity_curve(trades, starting_capital=Decimal("1000"))
        assert result[0].equity == Decimal("1100")
        assert result[1].equity == Decimal("1300")
        assert result[2].equity == Decimal("1250")

    @pytest.mark.unit
    def test_sorted_by_closed_at(self) -> None:
        """Equity curve must be ordered by closed_at ascending."""
        base = _NOW
        t_late = _make_trade_read(
            pnl=Decimal("50"),
            opened_at=base,
            closed_at=base + timedelta(hours=5),
        )
        t_early = _make_trade_read(
            pnl=Decimal("100"),
            opened_at=base,
            closed_at=base + timedelta(hours=1),
        )
        result = compute_equity_curve([t_late, t_early])
        # t_early should come first
        assert result[0].pnl == Decimal("100")
        assert result[1].pnl == Decimal("50")

    @pytest.mark.unit
    def test_pnl_field_set_correctly(self) -> None:
        """Each equity curve point should carry the trade's own PnL."""
        trades = [
            _make_trade_read(pnl=Decimal("77")),
        ]
        result = compute_equity_curve(trades)
        assert result[0].pnl == Decimal("77")


# ─── compute_drawdown_curve ───────────────────────────────────────────────────


class TestComputeDrawdownCurve:
    """Tests for :func:`compute_drawdown_curve`."""

    @pytest.mark.unit
    def test_empty_curve(self) -> None:
        """Should return empty list and zero drawdowns for an empty curve."""
        points, max_dd, max_dd_abs = compute_drawdown_curve([])
        assert points == []
        assert max_dd == Decimal("0")
        assert max_dd_abs == Decimal("0")

    @pytest.mark.unit
    def test_no_drawdown_when_equity_always_rises(self) -> None:
        """Drawdown should be 0 when equity only increases."""
        curve = [
            _make_equity_point(Decimal("1000"), Decimal("100"), 0),
            _make_equity_point(Decimal("1100"), Decimal("100"), 1),
            _make_equity_point(Decimal("1200"), Decimal("100"), 2),
        ]
        points, max_dd, max_dd_abs = compute_drawdown_curve(
            curve, starting_capital=Decimal("900")
        )
        for p in points:
            assert p.drawdown == Decimal("0")
            assert p.drawdown_abs == Decimal("0")
        assert max_dd == Decimal("0")
        assert max_dd_abs == Decimal("0")

    @pytest.mark.unit
    def test_drawdown_calculation(self) -> None:
        """Drawdown should be (current - peak) / peak."""
        curve = [
            _make_equity_point(Decimal("1000"), Decimal("100"), 0),
            _make_equity_point(Decimal("800"), Decimal("-200"), 1),
        ]
        points, max_dd, max_dd_abs = compute_drawdown_curve(curve)
        # peak = 1000, current = 800 → dd = -200/1000 = -0.2
        assert points[1].drawdown == Decimal("-0.2")
        assert points[1].drawdown_abs == Decimal("-200")
        assert max_dd == Decimal("-0.2")
        assert max_dd_abs == Decimal("-200")

    @pytest.mark.unit
    def test_max_drawdown_is_worst(self) -> None:
        """max_drawdown should capture the worst point in the series."""
        curve = [
            _make_equity_point(Decimal("1000"), Decimal("0"), 0),
            _make_equity_point(Decimal("900"), Decimal("-100"), 1),
            _make_equity_point(Decimal("700"), Decimal("-200"), 2),
            _make_equity_point(Decimal("950"), Decimal("250"), 3),
        ]
        _, max_dd, _ = compute_drawdown_curve(curve)
        # Worst drawdown: (700-1000)/1000 = -0.3
        assert max_dd == Decimal("-0.3")

    @pytest.mark.unit
    def test_drawdown_resets_after_new_peak(self) -> None:
        """After the equity reaches a new peak, drawdown should return to 0."""
        curve = [
            _make_equity_point(Decimal("1000"), Decimal("100"), 0),
            _make_equity_point(Decimal("800"), Decimal("-200"), 1),
            _make_equity_point(Decimal("1200"), Decimal("400"), 2),
        ]
        points, _, _ = compute_drawdown_curve(curve)
        assert points[2].drawdown == Decimal("0")
        assert points[2].drawdown_abs == Decimal("0")


# ─── compute_sharpe_ratio ─────────────────────────────────────────────────────


class TestComputeSharpeRatio:
    """Tests for :func:`compute_sharpe_ratio`."""

    @pytest.mark.unit
    def test_returns_none_for_empty_list(self) -> None:
        """Should return None for an empty trade list."""
        assert compute_sharpe_ratio([]) is None

    @pytest.mark.unit
    def test_returns_none_for_single_trade(self) -> None:
        """Should return None for a single closed trade."""
        result = compute_sharpe_ratio([_make_trade_read(pnl=Decimal("100"))])
        assert result is None

    @pytest.mark.unit
    def test_returns_none_for_open_trades(self) -> None:
        """Should return None when all trades are open (no closed_at)."""
        t = TradeRead(
            id=uuid.uuid4(),
            symbol="AAPL",
            direction=Direction.LONG,
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("10"),
            entry_price=Decimal("100"),
            exit_price=None,
            stop_loss=None,
            take_profit=None,
            opened_at=_NOW,
            closed_at=None,
            pnl=None,
            commission=Decimal("0"),
            journal=None,
            created_at=_NOW,
            updated_at=_NOW,
        )
        assert compute_sharpe_ratio([t, t]) is None

    @pytest.mark.unit
    def test_returns_decimal_for_two_trades(self) -> None:
        """Should return a Decimal for at least two closed trades on different days."""
        base = _NOW
        t1 = _make_trade_read(
            pnl=Decimal("100"),
            opened_at=base,
            closed_at=base,
        )
        t2 = _make_trade_read(
            pnl=Decimal("200"),
            opened_at=base + timedelta(days=1),
            closed_at=base + timedelta(days=1),
        )
        result = compute_sharpe_ratio([t1, t2])
        assert result is not None
        assert isinstance(result, Decimal)

    @pytest.mark.unit
    def test_returns_none_when_std_is_zero(self) -> None:
        """Should return None when all daily PnL values are identical (std = 0)."""
        base = _NOW
        trades = [
            _make_trade_read(
                pnl=Decimal("100"),
                opened_at=base + timedelta(days=i),
                closed_at=base + timedelta(days=i),
            )
            for i in range(5)
        ]
        # All PnL values are the same → std = 0 → Sharpe undefined
        result = compute_sharpe_ratio(trades)
        assert result is None
