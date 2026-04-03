"""Pure utility functions for computing trading performance metrics.

All functions in this module are stateless and have no side effects.
They do not import from ``app.repositories``, ``app.services``, or
``app.api``.  Database access and HTTP concepts are strictly forbidden
here.
"""

from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from math import sqrt
from typing import TYPE_CHECKING

from app.schemas.metrics import DrawdownPoint, EquityCurvePoint, TradeMetrics

if TYPE_CHECKING:
    from app.schemas.trade import TradeRead

# ─── Constants ────────────────────────────────────────────────────────────────

_ZERO = Decimal("0")
_ONE = Decimal("1")
_TRADING_DAYS_PER_YEAR = Decimal("252")


# ─── Public API ───────────────────────────────────────────────────────────────


def compute_trade_metrics(trades: "list[TradeRead]") -> TradeMetrics:
    """Compute aggregate performance metrics from a list of closed trades.

    Only trades whose ``pnl`` field is not ``None`` are included in the
    calculation.  Open trades (``pnl is None``) are silently skipped.

    Args:
        trades: A list of :class:`~app.schemas.trade.TradeRead` DTOs.

    Returns:
        A populated :class:`~app.schemas.metrics.TradeMetrics` instance.
    """
    # Filter to trades that have a realised PnL.
    # Prefer net_pnl when available (net of commissions); fall back to pnl.
    closed = [
        t
        for t in trades
        if (getattr(t, "net_pnl", None) is not None)
        or (getattr(t, "pnl", None) is not None)
    ]
    total = len(closed)

    if total == 0:
        return TradeMetrics(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            breakeven_trades=0,
            win_rate=_ZERO,
            loss_rate=_ZERO,
            avg_win=_ZERO,
            avg_loss=_ZERO,
            profit_factor=None,
            expectancy=_ZERO,
            total_pnl=_ZERO,
            gross_profit=_ZERO,
            gross_loss=_ZERO,
            max_consecutive_wins=0,
            max_consecutive_losses=0,
            avg_trade_duration_seconds=None,
            sharpe_ratio=None,
        )

    # Use net_pnl when present so aggregate metrics reflect fees/commissions.
    pnl_series: list[Decimal] = [
        t.net_pnl if getattr(t, "net_pnl", None) is not None else t.pnl for t in closed
    ]  # type: ignore[misc]

    wins = [p for p in pnl_series if p > _ZERO]
    losses = [p for p in pnl_series if p < _ZERO]
    breakevens = [p for p in pnl_series if p == _ZERO]

    n_wins = len(wins)
    n_losses = len(losses)
    n_breakeven = len(breakevens)

    win_rate = Decimal(n_wins) / Decimal(total)
    loss_rate = Decimal(n_losses) / Decimal(total)

    avg_win = (sum(wins, _ZERO) / Decimal(n_wins)) if n_wins else _ZERO
    avg_loss = (sum(losses, _ZERO) / Decimal(n_losses)) if n_losses else _ZERO

    gross_profit = sum(wins, _ZERO)
    gross_loss = sum(losses, _ZERO)
    total_pnl = sum(pnl_series, _ZERO)

    profit_factor: Decimal | None = None
    if n_losses > 0 and gross_loss != _ZERO:
        profit_factor = gross_profit / abs(gross_loss)

    expectancy = win_rate * avg_win + loss_rate * avg_loss

    max_cons_wins, max_cons_losses = compute_consecutive_runs(pnl_series)

    # Duration: only trades where both opened_at and closed_at are available.
    durations = [
        (t.closed_at - t.opened_at).total_seconds()
        for t in closed
        if t.closed_at is not None and t.opened_at is not None
    ]
    avg_duration: float | None = sum(durations) / len(durations) if durations else None

    sharpe = compute_sharpe_ratio(closed)

    return TradeMetrics(
        total_trades=total,
        winning_trades=n_wins,
        losing_trades=n_losses,
        breakeven_trades=n_breakeven,
        win_rate=win_rate,
        loss_rate=loss_rate,
        avg_win=avg_win,
        avg_loss=avg_loss,
        profit_factor=profit_factor,
        expectancy=expectancy,
        total_pnl=total_pnl,
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        max_consecutive_wins=max_cons_wins,
        max_consecutive_losses=max_cons_losses,
        avg_trade_duration_seconds=avg_duration,
        sharpe_ratio=sharpe,
    )


def compute_equity_curve(
    trades: "list[TradeRead]",
    starting_capital: Decimal = _ZERO,
) -> list[EquityCurvePoint]:
    """Build the cumulative equity curve from a list of closed trades.

    Only trades with a ``pnl`` value and a ``closed_at`` timestamp are
    included.  Trades are sorted by ``closed_at`` ascending before
    processing.

    Args:
        trades: A list of :class:`~app.schemas.trade.TradeRead` DTOs.
        starting_capital: The initial equity value before any trades.
            Defaults to ``Decimal("0")``.

    Returns:
        An ordered list of :class:`~app.schemas.metrics.EquityCurvePoint`
        instances, one per qualifying trade.
    """
    # Collect only trades that have both pnl and closed_at set.
    eligible: list[tuple[datetime, Decimal]] = []
    for t in trades:
        # Prefer net_pnl for equity updates when available.
        pnl_value = (
            getattr(t, "net_pnl", None)
            if getattr(t, "net_pnl", None) is not None
            else getattr(t, "pnl", None)
        )
        if pnl_value is not None and t.closed_at is not None:
            eligible.append((t.closed_at, pnl_value))

    # Sort by closed_at ascending.
    eligible.sort(key=lambda pair: pair[0])

    points: list[EquityCurvePoint] = []
    running_equity = starting_capital

    for closed_at, pnl in eligible:
        running_equity = running_equity + pnl
        # Ensure the timestamp is timezone-aware.
        ts = (
            closed_at if closed_at.tzinfo is not None else closed_at.replace(tzinfo=UTC)
        )
        points.append(EquityCurvePoint(timestamp=ts, equity=running_equity, pnl=pnl))

    return points


def compute_drawdown_curve(
    equity_curve: list[EquityCurvePoint],
    starting_capital: Decimal = _ZERO,
) -> tuple[list[DrawdownPoint], Decimal, Decimal]:
    """Compute the drawdown time series and maximum drawdown statistics.

    Drawdown at each point is defined as the relative decline from the
    running peak equity.  If the peak is zero the absolute difference is
    used to avoid division by zero.

    Args:
        equity_curve: Ordered list of equity curve points produced by
            :func:`compute_equity_curve`.
        starting_capital: The initial equity value used as the baseline
            peak.  Defaults to ``Decimal("0")``.

    Returns:
        A three-tuple of:

        - ``drawdown_curve``: list of :class:`~app.schemas.metrics.DrawdownPoint`.
        - ``max_drawdown_pct``: Most negative drawdown fraction (0.0 to -1.0).
        - ``max_drawdown_abs``: Most negative absolute drawdown.
    """
    if not equity_curve:
        return [], _ZERO, _ZERO

    peak = starting_capital
    max_drawdown_pct = _ZERO
    max_drawdown_abs = _ZERO
    points: list[DrawdownPoint] = []

    for ec_point in equity_curve:
        if ec_point.equity > peak:
            peak = ec_point.equity

        diff = ec_point.equity - peak  # always <= 0

        dd_pct = diff / peak if peak != _ZERO else diff

        if dd_pct < max_drawdown_pct:
            max_drawdown_pct = dd_pct
        if diff < max_drawdown_abs:
            max_drawdown_abs = diff

        points.append(
            DrawdownPoint(
                timestamp=ec_point.timestamp,
                drawdown=dd_pct,
                drawdown_abs=diff,
            )
        )

    return points, max_drawdown_pct, max_drawdown_abs


def compute_sharpe_ratio(trades: "list[TradeRead]") -> Decimal | None:
    """Compute the annualised Sharpe ratio from daily PnL.

    Daily PnL is constructed by summing the ``pnl`` of all closed trades
    for each calendar date (based on ``closed_at``).  The Sharpe ratio is
    annualised by multiplying by ``sqrt(252)`` (252 trading days per year).
    A risk-free rate of zero is assumed.

    Returns ``None`` when fewer than 2 closed trades are available, since
    standard deviation is undefined for a single observation.

    Args:
        trades: A list of :class:`~app.schemas.trade.TradeRead` DTOs.

    Returns:
        The annualised Sharpe ratio as a :class:`Decimal`, or ``None``.
    """
    closed = [t for t in trades if t.pnl is not None and t.closed_at is not None]
    if len(closed) < 2:
        return None

    # Group PnL by calendar date of closed_at.
    daily_pnl: dict[date, Decimal] = defaultdict(lambda: _ZERO)
    for trade in closed:
        closed_date = trade.closed_at.date()  # type: ignore[union-attr]
        pnl: Decimal = trade.pnl  # type: ignore[assignment]
        daily_pnl[closed_date] += pnl

    series = list(daily_pnl.values())
    n = len(series)
    if n < 2:
        return None

    mean = sum(series, _ZERO) / Decimal(n)
    variance = sum((x - mean) ** 2 for x in series) / Decimal(n - 1)

    try:
        std = Decimal(sqrt(float(variance)))
    except (InvalidOperation, ValueError):
        return None

    if std == _ZERO:
        return None

    sharpe = (mean / std) * Decimal(sqrt(float(_TRADING_DAYS_PER_YEAR)))
    return sharpe


def compute_consecutive_runs(pnl_series: list[Decimal]) -> tuple[int, int]:
    """Compute the maximum consecutive winning and losing streaks.

    A "win" is any trade with PnL > 0 and a "loss" is any trade with
    PnL < 0.  Break-even trades (PnL == 0) reset the streak counter.

    Args:
        pnl_series: Ordered list of PnL values (one per trade).

    Returns:
        A two-tuple of ``(max_consecutive_wins, max_consecutive_losses)``.
    """
    max_wins = 0
    max_losses = 0
    cur_wins = 0
    cur_losses = 0

    for pnl in pnl_series:
        if pnl > _ZERO:
            cur_wins += 1
            cur_losses = 0
        elif pnl < _ZERO:
            cur_losses += 1
            cur_wins = 0
        else:
            # Break-even trade resets both streaks.
            cur_wins = 0
            cur_losses = 0

        if cur_wins > max_wins:
            max_wins = cur_wins
        if cur_losses > max_losses:
            max_losses = cur_losses

    return max_wins, max_losses
