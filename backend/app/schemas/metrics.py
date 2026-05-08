"""Pydantic DTOs for performance metrics and time-series aggregation."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class TradeMetrics(BaseModel):
    """Aggregate performance metrics computed from a set of closed trades.

    Attributes:
        total_trades: Total number of closed trades with a PnL value.
        winning_trades: Number of trades with PnL > 0.
        losing_trades: Number of trades with PnL < 0.
        breakeven_trades: Number of trades with PnL == 0.
        win_rate: Fraction of winning trades over total (0.0–1.0).
        loss_rate: Fraction of losing trades over total (0.0–1.0).
        avg_win: Average PnL of winning trades.
        avg_loss: Average PnL of losing trades (negative value).
        profit_factor: Gross profit divided by the absolute gross loss.
            ``None`` when there are no losing trades.
        expectancy: Expected PnL per trade:
            ``win_rate * avg_win + loss_rate * avg_loss``.
        total_pnl: Sum of PnL across all closed trades.
        gross_profit: Sum of PnL for winning trades only (positive).
        gross_loss: Sum of PnL for losing trades only (negative).
        max_consecutive_wins: Longest winning streak.
        max_consecutive_losses: Longest losing streak.
        avg_trade_duration_seconds: Mean duration between ``opened_at`` and
            ``closed_at`` in seconds. ``None`` if no trade has both timestamps.
        sharpe_ratio: Annualised Sharpe ratio (risk-free rate = 0), using
            daily PnL grouped by ``closed_at`` date. ``None`` if fewer than
            2 closed trades exist.
    """

    total_trades: int = Field(
        ...,
        description="Total number of closed trades included in this computation.",
        examples=[42],
    )
    winning_trades: int = Field(
        ...,
        description="Number of trades with a positive PnL.",
        examples=[28],
    )
    losing_trades: int = Field(
        ...,
        description="Number of trades with a negative PnL.",
        examples=[12],
    )
    breakeven_trades: int = Field(
        ...,
        description="Number of trades with a PnL of exactly zero.",
        examples=[2],
    )
    win_rate: Decimal = Field(
        ...,
        description=("Fraction of winning trades over the total number of trades (0.0–1.0). A value of 0.667 means 66.7 % of trades were winners."),
        examples=["0.6667"],
    )
    loss_rate: Decimal = Field(
        ...,
        description=("Fraction of losing trades over the total number of trades (0.0–1.0). Complements win_rate."),
        examples=["0.2857"],
    )
    avg_win: Decimal = Field(
        ...,
        description="Average PnL of winning trades in account currency.",
        examples=["325.50"],
    )
    avg_loss: Decimal = Field(
        ...,
        description=("Average PnL of losing trades in account currency (negative value)."),
        examples=["-145.20"],
    )
    profit_factor: Decimal | None = Field(
        ...,
        description=(
            "Gross profit divided by the absolute value of gross loss. "
            "A profit factor above 1.0 means the strategy is profitable overall. "
            "Null when there are no losing trades."
        ),
        examples=["2.24", None],
    )
    expectancy: Decimal = Field(
        ...,
        description=("Expected PnL per trade: win_rate × avg_win + loss_rate × avg_loss. Positive expectancy means the strategy is profitable on average."),
        examples=["175.83"],
    )
    total_pnl: Decimal = Field(
        ...,
        description="Sum of PnL across all closed trades in account currency.",
        examples=["7384.50"],
    )
    gross_profit: Decimal = Field(
        ...,
        description="Sum of PnL for winning trades only (always >= 0).",
        examples=["9114.00"],
    )
    gross_loss: Decimal = Field(
        ...,
        description="Sum of PnL for losing trades only (always <= 0).",
        examples=["-1742.40"],
    )
    max_consecutive_wins: int = Field(
        ...,
        description="Length of the longest consecutive winning streak.",
        examples=[7],
    )
    max_consecutive_losses: int = Field(
        ...,
        description="Length of the longest consecutive losing streak.",
        examples=[3],
    )
    avg_trade_duration_seconds: float | None = Field(
        ...,
        description=("Average duration of a trade from open to close in seconds. Null when no trade has both opened_at and closed_at set."),
        examples=[14400.0, None],
    )
    sharpe_ratio: Decimal | None = Field(
        ...,
        description=(
            "Annualised Sharpe ratio assuming a risk-free rate of zero, "
            "computed from daily PnL grouped by closed_at date. "
            "Null when fewer than 2 closed trades are available."
        ),
        examples=["1.42", None],
    )


class DrawdownPoint(BaseModel):
    """A single point in the portfolio drawdown time series.

    Attributes:
        timestamp: UTC timestamp of the trade that caused this drawdown reading.
        drawdown: Drawdown as a fraction of the peak equity (0.0 to -1.0).
            For example, -0.15 represents a 15 % drawdown from the peak.
        drawdown_abs: Absolute drawdown in account currency (always <= 0).
    """

    timestamp: datetime = Field(
        ...,
        description=("Timezone-aware UTC timestamp of the trade that caused this drawdown data point."),
        examples=["2024-05-10T14:30:00Z"],
    )
    drawdown: Decimal = Field(
        ...,
        description=("Drawdown as a fraction of the peak equity (range: 0.0 to -1.0). -0.15 means a 15 % drawdown from the running equity peak."),
        examples=["-0.1500"],
    )
    drawdown_abs: Decimal = Field(
        ...,
        description=("Absolute drawdown in account currency. Always zero or negative. For example, -1500.00 means the portfolio is $1 500 below its peak."),
        examples=["-1500.00"],
    )


class EquityCurvePoint(BaseModel):
    """A single point in the cumulative equity curve.

    Attributes:
        timestamp: UTC timestamp of the trade that updated the equity value.
        equity: Cumulative PnL from the starting capital at this point.
        pnl: The PnL contribution of the individual trade at this point.
    """

    timestamp: datetime = Field(
        ...,
        description=("Timezone-aware UTC timestamp of the trade that produced this equity curve data point."),
        examples=["2024-05-10T14:30:00Z"],
    )
    equity: Decimal = Field(
        ...,
        description=("Cumulative PnL from the starting capital up to and including this trade. Equal to starting_capital + sum(pnl up to this point)."),
        examples=["10475.00"],
    )
    pnl: Decimal = Field(
        ...,
        description=("PnL of the individual trade that caused this equity curve update."),
        examples=["475.00", "-120.50"],
    )


class MetricsSummary(BaseModel):
    """Complete metrics summary combining aggregate stats and time-series curves.

    Attributes:
        metrics: Aggregate performance metrics (win rate, Sharpe, etc.).
        max_drawdown: Worst drawdown fraction experienced (0.0 to -1.0).
        max_drawdown_abs: Worst absolute drawdown in account currency.
        equity_curve: Ordered list of equity curve data points.
        drawdown_curve: Ordered list of drawdown data points.
    """

    metrics: TradeMetrics = Field(
        ...,
        description=("Aggregate performance metrics computed from all qualifying trades."),
        examples=[
            {
                "total_trades": 42,
                "winning_trades": 28,
                "losing_trades": 12,
                "breakeven_trades": 2,
                "win_rate": "0.6667",
                "loss_rate": "0.2857",
                "avg_win": "325.50",
                "avg_loss": "-145.20",
                "profit_factor": "2.24",
                "expectancy": "175.83",
                "total_pnl": "7384.50",
                "gross_profit": "9114.00",
                "gross_loss": "-1742.40",
                "max_consecutive_wins": 7,
                "max_consecutive_losses": 3,
                "avg_trade_duration_seconds": 14400.0,
                "sharpe_ratio": "1.42",
            }
        ],
    )
    max_drawdown: Decimal = Field(
        ...,
        description=(
            "The worst (most negative) drawdown fraction over the observed period (range: 0.0 to -1.0). Zero when the equity never fell below the peak."
        ),
        examples=["-0.2200"],
    )
    max_drawdown_abs: Decimal = Field(
        ...,
        description=("The worst absolute drawdown in account currency over the observed period. Always zero or negative."),
        examples=["-2200.00"],
    )
    equity_curve: list[EquityCurvePoint] = Field(
        ...,
        description=("Ordered list of equity curve data points, one per closed trade, capped at EQUITY_CURVE_MAX_POINTS entries."),
        examples=[
            [
                {
                    "timestamp": "2024-01-15T10:30:00Z",
                    "equity": "10475.00",
                    "pnl": "475.00",
                },
                {
                    "timestamp": "2024-01-22T14:05:00Z",
                    "equity": "10354.50",
                    "pnl": "-120.50",
                },
            ]
        ],
    )
    drawdown_curve: list[DrawdownPoint] = Field(
        ...,
        description=("Ordered list of drawdown data points corresponding to each equity curve entry."),
        examples=[
            [
                {
                    "timestamp": "2024-01-15T10:30:00Z",
                    "drawdown": "0.0000",
                    "drawdown_abs": "0.00",
                },
                {
                    "timestamp": "2024-01-22T14:05:00Z",
                    "drawdown": "-0.0115",
                    "drawdown_abs": "-120.50",
                },
            ]
        ],
    )
