"""Pydantic DTOs for time-series and aggregation endpoints."""

import datetime as dt
from decimal import Decimal

from pydantic import BaseModel, Field


class DailyPnl(BaseModel):
    """Aggregated PnL for a single trading day.

    Attributes:
        date: The calendar date of the trading day (UTC).
        pnl: Total PnL realised across all closed trades on this day.
        trade_count: Number of closed trades that day.
        cumulative_pnl: Running cumulative PnL up to and including this day,
            ordered chronologically from the earliest available trade.
    """

    date: dt.date = Field(
        ...,
        description="Calendar date of the trading day (UTC).",
        examples=["2024-05-10"],
    )
    pnl: Decimal = Field(
        ...,
        description=(
            "Total realised PnL for this day, summed across all closed trades "
            "whose ``closed_at`` date matches this day."
        ),
        examples=["475.00", "-120.50"],
    )
    trade_count: int = Field(
        ...,
        description="Number of closed trades with a PnL value that closed on this day.",
        examples=[3, 1],
    )
    cumulative_pnl: Decimal = Field(
        ...,
        description=(
            "Running cumulative PnL up to and including this trading day, "
            "computed from the earliest available closed trade in the result set."
        ),
        examples=["1250.00", "-45.00"],
    )


class MonthlyPnl(BaseModel):
    """Aggregated PnL for a calendar month.

    Attributes:
        year: Four-digit calendar year.
        month: Calendar month (1–12).
        pnl: Total PnL realised during this month.
        trade_count: Number of closed trades during this month.
        win_rate: Fraction of winning trades (PnL > 0) for this month (0.0–1.0).
    """

    year: int = Field(
        ...,
        description="Four-digit calendar year.",
        examples=[2024, 2025],
    )
    month: int = Field(
        ...,
        description="Calendar month number (1 = January, 12 = December).",
        examples=[1, 6, 12],
    )
    pnl: Decimal = Field(
        ...,
        description="Total realised PnL for this calendar month.",
        examples=["3200.00", "-540.50"],
    )
    trade_count: int = Field(
        ...,
        description="Total number of closed trades during this calendar month.",
        examples=[15, 4],
    )
    win_rate: Decimal = Field(
        ...,
        description=(
            "Fraction of winning trades (PnL > 0) over the total trade count "
            "for this month (0.0–1.0). Zero when ``trade_count`` is zero."
        ),
        examples=["0.6667", "0.7500", "0.0000"],
    )


class PnlBySymbol(BaseModel):
    """Aggregated PnL grouped by ticker symbol.

    Attributes:
        symbol: Ticker symbol of the traded instrument.
        total_pnl: Sum of realised PnL across all trades for this symbol.
        trade_count: Total number of closed trades for this symbol.
        win_rate: Fraction of winning trades for this symbol (0.0–1.0).
        avg_pnl: Average PnL per trade for this symbol.
    """

    symbol: str = Field(
        ...,
        description=(
            "Ticker symbol of the traded instrument (e.g. 'AAPL', 'ES', 'EURUSD')."
        ),
        examples=["AAPL", "ES", "EURUSD"],
    )
    total_pnl: Decimal = Field(
        ...,
        description="Sum of realised PnL across all closed trades for this symbol.",
        examples=["4250.00", "-320.00"],
    )
    trade_count: int = Field(
        ...,
        description="Total number of closed trades with a PnL value for this symbol.",
        examples=[18, 5],
    )
    win_rate: Decimal = Field(
        ...,
        description=(
            "Fraction of trades with a positive PnL for this symbol (0.0–1.0)."
        ),
        examples=["0.7222", "0.4000"],
    )
    avg_pnl: Decimal = Field(
        ...,
        description=(
            "Average PnL per trade for this symbol "
            "(``total_pnl / trade_count`` when ``trade_count > 0``, else zero)."
        ),
        examples=["236.11", "-64.00"],
    )


class PnlByAssetClass(BaseModel):
    """Aggregated PnL grouped by asset class.

    Attributes:
        asset_class: Asset class label (e.g. ``"EQUITY"``, ``"OPTION"``).
        total_pnl: Sum of realised PnL across all trades for this asset class.
        trade_count: Total number of closed trades for this asset class.
        win_rate: Fraction of winning trades for this asset class (0.0–1.0).
    """

    asset_class: str = Field(
        ...,
        description=(
            "Asset class of the traded instrument. "
            "One of: EQUITY, OPTION, FUTURE, FOREX, CRYPTO."
        ),
        examples=["EQUITY", "OPTION", "FUTURE", "FOREX", "CRYPTO"],
    )
    total_pnl: Decimal = Field(
        ...,
        description=(
            "Sum of realised PnL across all closed trades for this asset class."
        ),
        examples=["6800.00", "-1200.00"],
    )
    trade_count: int = Field(
        ...,
        description=(
            "Total number of closed trades with a PnL value for this asset class."
        ),
        examples=[32, 8],
    )
    win_rate: Decimal = Field(
        ...,
        description=(
            "Fraction of trades with a positive PnL for this asset class (0.0–1.0)."
        ),
        examples=["0.6875", "0.3750"],
    )


class ReturnDistribution(BaseModel):
    """A single histogram bucket for the PnL return distribution.

    Attributes:
        bucket_min: Inclusive lower bound of this PnL bucket.
        bucket_max: Exclusive upper bound of this PnL bucket
            (the last bucket is inclusive on both ends).
        count: Number of trades whose PnL falls within this bucket.
        frequency: Fraction of total trades in this bucket (0.0–1.0).
    """

    bucket_min: Decimal = Field(
        ...,
        description=(
            "Inclusive lower bound of this PnL histogram bucket in account currency."
        ),
        examples=["-500.00", "0.00", "250.00"],
    )
    bucket_max: Decimal = Field(
        ...,
        description=(
            "Exclusive upper bound of this PnL histogram bucket in account currency. "
            "The final bucket is inclusive on the upper bound."
        ),
        examples=["-250.00", "250.00", "500.00"],
    )
    count: int = Field(
        ...,
        description="Number of closed trades whose PnL falls within this bucket.",
        examples=[4, 12, 1],
    )
    frequency: Decimal = Field(
        ...,
        description=(
            "Fraction of total closed trades that fall within this bucket (0.0–1.0). "
            "Sum of all bucket frequencies equals 1.0 when trades exist."
        ),
        examples=["0.0952", "0.2857", "0.0238"],
    )
