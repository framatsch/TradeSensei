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

"""Pydantic schemas for dashboard views, analytics, and attribution APIs."""

import datetime as dt
import uuid
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.trade import Direction

CurrencyMode = Literal["NATIVE", "NORMALIZED"]


class DashboardFilterConfig(BaseModel):
    """Validated analytics filter configuration stored in saved views."""

    date_from: dt.date | None = Field(
        default=None,
        description="Optional inclusive start date for closed trade filtering.",
    )
    date_to: dt.date | None = Field(
        default=None,
        description="Optional inclusive end date for closed trade filtering.",
    )
    playbook_ids: list[uuid.UUID] | None = Field(
        default=None,
        description="Optional list of playbook IDs used to filter trades.",
    )
    taxonomy_ids: list[uuid.UUID] | None = Field(
        default=None,
        description="Optional list of taxonomy IDs used to filter trades.",
    )
    status: Literal["open", "closed"] | None = Field(
        default=None,
        description="Optional status filter. If 'open', only open trades are included. If 'closed', only closed trades are included. If None, both are included.",
    )
    direction: Direction | None = Field(
        default=None,
        description="Optional trade direction filter.",
    )
    account_ids: list[uuid.UUID] | None = Field(
        default=None,
        description="Optional list of account IDs used to filter trades.",
    )
    currency_mode: CurrencyMode = Field(
        default="NATIVE",
        description="Currency handling mode for monetary analytics fields.",
    )
    normalize_to: str | None = Field(
        default=None,
        min_length=3,
        max_length=3,
        description=("ISO-4217 target currency used when currency_mode is NORMALIZED."),
    )
    schema_version: str = Field(
        default="1",
        alias="_schema_version",
        serialization_alias="_schema_version",
        description="Filter schema version for future compatibility handling.",
    )

    @model_validator(mode="after")
    def validate_ranges_and_currency(self) -> "DashboardFilterConfig":
        """Validate date range ordering and normalization requirements."""
        if self.date_from is not None and self.date_to is not None and self.date_from > self.date_to:
            raise ValueError("date_from must not be later than date_to")

        if self.currency_mode == "NORMALIZED" and not self.normalize_to:
            raise ValueError("normalize_to is required when currency_mode=NORMALIZED")

        return self


class SavedDashboardViewCreate(BaseModel):
    """Request body for creating a saved dashboard view."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="User-facing view name.",
    )
    filter_config: DashboardFilterConfig = Field(
        ...,
        description="Persisted analytics filter configuration for this view.",
    )


class SavedDashboardViewUpdate(BaseModel):
    """Request body for patching a saved dashboard view."""

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Updated user-facing view name.",
    )
    filter_config: DashboardFilterConfig | None = Field(
        default=None,
        description="Updated analytics filter configuration.",
    )


class SavedDashboardViewRead(BaseModel):
    """Response schema for saved dashboard views."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID = Field(..., description="Saved view ID.")
    user_id: uuid.UUID = Field(..., description="Owner user ID.")
    portfolio_id: uuid.UUID = Field(..., description="Bound portfolio ID.")
    name: str = Field(..., description="User-facing view name.")
    filter_config: DashboardFilterConfig = Field(
        ...,
        description="Persisted analytics filter configuration.",
    )
    created_at: dt.datetime = Field(..., description="Creation timestamp in UTC.")
    updated_at: dt.datetime = Field(..., description="Last update timestamp in UTC.")


class EquityCurvePoint(BaseModel):
    """A single point in an analytics equity curve."""

    date: dt.date = Field(..., description="Calendar date for this equity point.")
    equity: Decimal = Field(
        ...,
        description="Cumulative PnL at this point in the reported currency.",
    )
    currency: str = Field(
        ...,
        min_length=3,
        max_length=3,
        description="ISO-4217 currency of this equity value.",
    )


class DrawdownPoint(BaseModel):
    """A single point in an analytics drawdown curve."""

    date: dt.date = Field(..., description="Calendar date for this drawdown point.")
    drawdown_pct: Decimal = Field(
        ...,
        description="Drawdown fraction from running equity peak (0 to -1).",
    )
    drawdown_abs: Decimal = Field(
        ...,
        description="Absolute drawdown value in the reported currency.",
    )


class PerCurrencySummary(BaseModel):
    """Monetary summary for one currency bucket in NATIVE mixed mode."""

    currency: str = Field(
        ...,
        min_length=3,
        max_length=3,
        description="ISO-4217 currency code for this bucket.",
    )
    total_trades: int = Field(..., description="Number of trades in this currency.")
    winning_trades: int = Field(..., description="Winning trades in this currency.")
    losing_trades: int = Field(..., description="Losing trades in this currency.")
    gross_profit: Decimal = Field(..., description="Gross profit in this currency.")
    gross_loss: Decimal = Field(..., description="Gross loss in this currency.")
    avg_win: Decimal = Field(..., description="Average winning PnL in this currency.")
    avg_loss: Decimal = Field(..., description="Average losing PnL in this currency.")
    expectancy: Decimal = Field(..., description="Expectancy in this currency.")


class AnalyticsSummary(BaseModel):
    """Computed analytics summary response."""

    win_rate: Decimal = Field(..., description="Winning trade ratio from 0 to 1.")
    profit_factor: Decimal | None = Field(
        ...,
        description="Gross profit divided by absolute gross loss.",
    )
    expectancy: Decimal | None = Field(
        ...,
        description="Expected PnL per trade in the reported currency.",
    )
    sharpe_ratio: Decimal | None = Field(
        ...,
        description="Annualized Sharpe ratio; null when undefined.",
    )
    total_trades: int = Field(..., description="Number of included trades.")
    winning_trades: int = Field(..., description="Trades with positive PnL.")
    losing_trades: int = Field(..., description="Trades with negative PnL.")
    total_pnl: Decimal | None = Field(
        ...,
        description="Net sum of all trade PnL values (gross_profit + gross_loss). Null in mixed-currency native mode.",
    )
    gross_profit: Decimal | None = Field(
        ...,
        description="Sum of positive PnL values in reported currency.",
    )
    gross_loss: Decimal | None = Field(
        ...,
        description="Sum of negative PnL values in reported currency.",
    )
    avg_win: Decimal | None = Field(..., description="Average winning trade PnL.")
    avg_loss: Decimal | None = Field(..., description="Average losing trade PnL.")
    max_consecutive_wins: int = Field(
        ...,
        description="Longest consecutive winning streak.",
    )
    max_consecutive_losses: int = Field(
        ...,
        description="Longest consecutive losing streak.",
    )
    avg_trade_duration_hours: Decimal | None = Field(
        ...,
        description="Average trade duration in hours.",
    )
    equity_curve: list[EquityCurvePoint] = Field(
        ...,
        description="Server-side computed and downsampled equity curve.",
    )
    drawdown_curve: list[DrawdownPoint] = Field(
        ...,
        description="Drawdown curve derived from the equity curve.",
    )
    max_drawdown: Decimal = Field(..., description="Worst drawdown percentage.")
    max_drawdown_abs: Decimal = Field(..., description="Worst absolute drawdown.")
    currency: str | None = Field(
        ...,
        description="Single response currency, or null for mixed native mode.",
    )
    multi_currency_warning: bool = Field(
        default=False,
        description="True when response spans multiple currencies in NATIVE mode.",
    )
    currencies: list[PerCurrencySummary] | None = Field(
        default=None,
        description="Per-currency monetary summaries for mixed native mode.",
    )
    fx_rate_missing_trade_ids: list[uuid.UUID] | None = Field(
        default=None,
        description="Trades excluded due to missing FX rates in NORMALIZED mode.",
    )


class MarketPhaseCorrelation(BaseModel):
    """Attribution bucket grouped by market phase."""

    market_phase: str = Field(
        ...,
        description="Raw market phase name from DailyCheckin.market_phase.",
    )
    label: str = Field(
        ...,
        description="Display label resolved from MarketPhaseDefinition or fallback.",
    )
    color_hex: str | None = Field(
        default=None,
        description="Display color resolved from MarketPhaseDefinition.",
    )
    trade_count: int = Field(..., description="Matched trades in this bucket.")
    win_rate: Decimal = Field(..., description="Winning trade ratio for this bucket.")
    profit_factor: Decimal | None = Field(
        ...,
        description="Profit factor for this bucket.",
    )
    avg_pnl: Decimal = Field(..., description="Average trade PnL in this bucket.")
    total_pnl: Decimal = Field(..., description="Total PnL in this bucket.")
    currency: str = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Currency of bucket monetary values.",
    )


class AttributionResponse(BaseModel):
    """Response payload for market phase attribution endpoint."""

    buckets: list[MarketPhaseCorrelation] = Field(
        ...,
        description="Attribution buckets grouped by market phase.",
    )
    unmatched_trade_count: int = Field(
        ...,
        description="Trades without a check-in on close date.",
    )
    phase_unset_trade_count: int = Field(
        ...,
        description="Trades with check-in but null market_phase.",
    )
    currency: str | None = Field(
        ...,
        description="Common currency when available; null for mixed buckets.",
    )


class AnalyticsSummaryRequest(BaseModel):
    """Request body for analytics summary computation."""

    filter_config: DashboardFilterConfig | None = Field(
        default=None,
        description="Inline filter configuration.",
    )
    view_id: uuid.UUID | None = Field(
        default=None,
        description="Saved dashboard view ID used as filter alias.",
    )

    @model_validator(mode="after")
    def validate_exactly_one_source(self) -> "AnalyticsSummaryRequest":
        """Require exactly one of filter_config or view_id."""
        provided = int(self.filter_config is not None) + int(self.view_id is not None)
        if provided != 1:
            raise ValueError("exactly one of filter_config or view_id must be provided")
        return self


AxisType = Literal["checkin_annotation", "checkin_taxonomy", "trade_annotation", "trade_taxonomy"]


class MetadataCorrelationRequest(BaseModel):
    """Request body for metadata correlation computation."""

    x_axis_type: AxisType = Field(..., description="Type of metadata for the X axis.")
    x_axis_id: uuid.UUID = Field(..., description="ID of the metadata definition for the X axis.")
    y_axis_type: AxisType = Field(..., description="Type of metadata for the Y axis.")
    y_axis_id: uuid.UUID = Field(..., description="ID of the metadata definition for the Y axis.")
    base_asset: str | None = Field(
        default=None,
        description="Optional base asset to filter trades (e.g. BTC, ETH).",
    )
    filter_config: DashboardFilterConfig | None = Field(
        default=None,
        description="Inline filter configuration.",
    )
    view_id: uuid.UUID | None = Field(
        default=None,
        description="Saved dashboard view ID used as filter alias.",
    )

    @model_validator(mode="after")
    def validate_exactly_one_source(self) -> "MetadataCorrelationRequest":
        """Require exactly one of filter_config or view_id."""
        provided = int(self.filter_config is not None) + int(self.view_id is not None)
        if provided != 1:
            raise ValueError("exactly one of filter_config or view_id must be provided")
        return self


class MetadataCorrelationDataPoint(BaseModel):
    """A single correlated data point representing one check-in and one trade."""

    date: dt.date = Field(..., description="Calendar date of the check-in/trade.")
    trade_id: uuid.UUID = Field(..., description="ID of the matched trade.")
    trade_symbol: str = Field(..., description="Symbol of the matched trade.")
    trade_pnl: Decimal = Field(..., description="PnL of the matched trade.")
    x_value: float | str | None = Field(None, description="Resolved raw value for the X axis.")
    x_label: str | None = Field(None, description="Resolved display label for the X axis.")
    y_value: float | str | None = Field(None, description="Resolved raw value for the Y axis.")
    y_label: str | None = Field(None, description="Resolved display label for the Y axis.")


class MetadataCorrelationKPIs(BaseModel):
    """Aggregate KPIs for the correlated dataset."""

    win_rate: Decimal = Field(..., description="Win rate among all filtered trades.")
    max_drawdown_pct: Decimal = Field(..., description="Max drawdown percentage among all filtered trades.")
    matched_count: int = Field(..., description="Number of trades with valid data for both axes.")
    total_trades_count: int = Field(..., description="Total trades matching the global filter.")


class MetadataCorrelationResponse(BaseModel):
    """Response containing correlated metadata and KPIs."""

    kpis: MetadataCorrelationKPIs = Field(..., description="Aggregate KPIs.")
    data_points: list[MetadataCorrelationDataPoint] = Field(..., description="Correlated data points.")
    x_axis_data_type: str = Field(..., description="Data type of the X axis ('number', 'string', 'taxonomy').")
    y_axis_data_type: str = Field(..., description="Data type of the Y axis ('number', 'string', 'taxonomy').")
    x_axis_name: str = Field(..., description="Display name of the X axis.")
    y_axis_name: str = Field(..., description="Display name of the Y axis.")
