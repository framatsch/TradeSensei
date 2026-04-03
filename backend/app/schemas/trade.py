"""Pydantic DTOs for Trade request and response shapes."""

import contextlib
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.constants import NOTES_MAX_LENGTH, SYMBOL_MAX_LENGTH, SYMBOL_MIN_LENGTH
from app.models.trade import AssetClass, Direction
from app.schemas.note import TradeNoteRead
from app.schemas.tag import TagRead

# Sentinel singleton used to distinguish "field not provided" from "field set to None"

# Sentinel singleton used to distinguish "field not provided" from "field set to None"
_UNSET: object = object()


class TradePartialCloseRequest(BaseModel):
    """Payload for splitting an open trade by closing a portion of it.

    This request is used to 'trim' a position (e.g., selling 5 out of 20 shares).
    The original trade's quantity is reduced, and a new closed trade is
    created with the specified exit details and a deep copy of all metadata.

    Attributes:
        quantity: Amount to close (must be > 0 and <= original trade quantity).
        exit_price: Execution price for this partial close.
        closed_at: Timezone-aware UTC timestamp of the close.
        exit_commission: Additional commission paid for this exit.
    """

    quantity: Decimal = Field(..., gt=Decimal("0"))
    exit_price: Decimal = Field(..., ge=Decimal("0"))
    closed_at: datetime = Field(...)
    exit_commission: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))

    @field_validator("closed_at")
    @classmethod
    def check_utc(cls, v: datetime) -> datetime:
        """Ensure the timestamp is timezone-aware and set to UTC."""
        if v.tzinfo is None:
            raise ValueError("closed_at must be timezone-aware (UTC).")
        return v.astimezone(UTC) if v.tzinfo != UTC else v


class TradeCreate(BaseModel):
    """Internal schema for creating a new trade, including the resolved user_id.

    This schema is used by the service and repository layers only.
    The ``user_id`` field is injected by the route handler from the
    authenticated user — it is never supplied by an API client.

    See :class:`TradeCreateRequest` for the public-facing API request body.

    Attributes:
        user_id: UUID of the owning user — injected by the route handler.
        symbol: Ticker symbol (e.g. ``"AAPL"``).
        direction: Long or short.
        asset_class: Asset class of the instrument.
        quantity: Number of units / contracts traded.
        entry_price: Execution price at open.
        exit_price: Execution price at close (omit for open trades).
        stop_loss: Optional stop-loss price.
        take_profit: Optional take-profit price.
        opened_at: Timezone-aware UTC timestamp of position open.
        closed_at: Timezone-aware UTC timestamp of position close.
        pnl: Realised PnL (may be supplied manually; computed in later
            iterations).
        commission: Total commission paid; defaults to zero.
        notes: Free-text notes.
    """

    user_id: uuid.UUID | None = None
    broker_conid: str | None = Field(
        default=None, description="Broker contract identifier."
    )
    multiplier: int = Field(default=1, description="Contract multiplier.")
    symbol: str = Field(
        ...,
        min_length=SYMBOL_MIN_LENGTH,
        max_length=SYMBOL_MAX_LENGTH,
        description=(
            "Ticker symbol of the traded instrument. "
            "Maximum 30 characters (e.g. 'AAPL', 'EURUSD', 'CHTR  251003P00240000')."
        ),
        examples=["AAPL", "EURUSD", "BTCUSDT", "ES"],
    )
    direction: Direction = Field(
        ...,
        description=(
            "Trade direction — 'LONG' for a buy position, 'SHORT' for a sell position."
        ),
        examples=["LONG", "SHORT"],
    )
    asset_class: AssetClass = Field(
        ...,
        description=(
            "Asset class of the traded instrument. "
            "One of: EQUITY, OPTION, FUTURE, FOREX, CRYPTO."
        ),
        examples=["EQUITY", "FOREX", "CRYPTO"],
    )
    quantity: Decimal = Field(
        ...,
        ge=Decimal("0"),
        description=(
            "Number of units, shares, or contracts traded. Must be greater than zero."
        ),
        examples=["100", "1.5", "0.01"],
    )
    entry_price: Decimal = Field(
        ...,
        ge=Decimal("0"),
        description=(
            "Execution price at which the position was opened. "
            "Must be greater than zero."
        ),
        examples=["150.25", "1.0823", "42350.00"],
    )
    exit_price: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        description=(
            "Execution price at which the position was closed. "
            "Omit or set to null for trades that are still open."
        ),
        examples=["155.00", "1.0901", None],
    )
    stop_loss: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        description=(
            "Stop-loss price level for the trade. "
            "Omit or set to null if no stop-loss was set."
        ),
        examples=["148.00", "1.0780", None],
    )
    take_profit: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        description=(
            "Take-profit price level for the trade. "
            "Omit or set to null if no take-profit was set."
        ),
        examples=["158.00", "1.0950", None],
    )
    opened_at: datetime = Field(
        ...,
        description=(
            "Timezone-aware UTC timestamp of when the position was opened. "
            "Naive datetimes (without timezone info) are rejected."
        ),
        examples=["2024-03-15T09:30:00Z", "2024-03-15T09:30:00+00:00"],
    )
    closed_at: datetime | None = Field(
        default=None,
        description=(
            "Timezone-aware UTC timestamp of when the position was closed. "
            "Omit or set to null for trades that are still open. "
            "Naive datetimes are rejected."
        ),
        examples=["2024-03-15T15:45:00Z", None],
    )
    pnl: Decimal | None = Field(
        default=None,
        description=(
            "Realised profit or loss for this trade in account currency. "
            "Can be supplied manually; automated computation is planned "
            "for a later iteration. Null for open trades."
        ),
        examples=["475.00", "-120.50", None],
    )
    net_pnl: Decimal | None = Field(
        default=None,
        description=(
            "Realised net profit or loss for this trade in account currency. "
            "Null for open trades."
        ),
        examples=["473.50", "-123.70", None],
    )
    commission: Decimal = Field(
        default=Decimal("0"),
        ge=Decimal("0"),
        description="Total commission paid for this trade. Defaults to zero.",
        examples=["1.50", "3.20", "0"],
    )
    notes: str | None = Field(
        default=None,
        max_length=NOTES_MAX_LENGTH,
        description=(
            "Free-text notes attached to this trade, e.g. trade rationale, "
            "emotional state, or post-trade review."
        ),
        examples=["Breakout above 50-day MA. Tight stop below consolidation.", None],
    )
    tradingview_link: str | None = Field(
        default=None,
        description="Optional link to a TradingView chart for this trade.",
        examples=["https://www.tradingview.com/chart/...", None],
    )
    screenshots: list[str] | None = Field(
        default_factory=list,
        description="List of screenshot URLs for this trade.",
        examples=[["https://example.com/screenshot1.png"], []],
    )
    currency: str | None = Field(
        default=None,
        min_length=3,
        max_length=3,
        description=(
            "ISO-4217 currency code of the trade (e.g. 'USD'). "
            "Set automatically by broker importers."
        ),
        examples=["USD", None],
    )
    pnl_eur: Decimal | None = Field(
        default=None,
        description=(
            "Realised P&L converted to EUR at the official Bundesbank daily rate "
            "on the trade date. Null for open trades or when the rate is unavailable."
        ),
        examples=["432.50", "-98.20", None],
    )
    net_pnl_eur: Decimal | None = Field(
        default=None,
        description=(
            "Realised net P&L converted to EUR at the official Bundesbank daily rate "
            "on the trade date. Null for open trades or when the rate is unavailable."
        ),
        examples=["430.50", "-100.20", None],
    )
    account_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "UUID of the broker account this trade belongs to. "
            "Omit to create an unassigned trade."
        ),
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6", None],
    )
    playbook_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "UUID of the playbook (strategy) to associate with this trade. "
            "Omit or set to null for no playbook."
        ),
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6", None],
    )
    tag_ids: list[uuid.UUID] = Field(
        default_factory=list,
        description=(
            "List of tag UUIDs to attach to this trade. "
            "All UUIDs must belong to the authenticated user."
        ),
        examples=[["3fa85f64-5717-4562-b3fc-2c963f66afa6"], []],
    )
    broker_order_id: str | None = Field(
        default=None,
        max_length=100,
        description=(
            "External broker order identifier used for deduplication during "
            "live broker syncs. Set automatically by broker importers."
        ),
        examples=["1234567890", None],
    )
    broker_conid: str | None = Field(
        default=None,
        max_length=50,
        description="External broker contract identifier (e.g. IBKR conid).",
        examples=["357194941", None],
    )
    is_manually_edited: bool = Field(
        default=False,
        description=(
            "When True, this trade was manually corrected and will be "
            "skipped on subsequent broker re-imports."
        ),
        examples=[False, True],
    )
    db_trade_id: uuid.UUID | None = Field(
        default=None,
        exclude=True,
        description=(
            "Internal field — set by the import service when this TradeCreate "
            "originated from an existing open DB row that should be *updated* "
            "rather than inserted.  Never persisted to the database."
        ),
    )
    is_mixed_execution: bool = Field(
        default=False,
        exclude=True,
        description=(
            "Internal flag — set when IBKR openCloseIndicator='C;O'. "
            "Tells the aggregator this execution flips the position."
        ),
    )

    @field_validator("opened_at", "closed_at", mode="after")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        """Reject naive datetimes — all timestamps must carry timezone info.

        Args:
            value: Parsed datetime value (already coerced from string by Pydantic).

        Returns:
            The original value unchanged if it is timezone-aware or None.

        Raises:
            ValueError: If the supplied ``datetime`` has no ``tzinfo``.
        """
        if value is not None and value.tzinfo is None:
            raise ValueError("Datetime must be timezone-aware (include UTC offset).")
        return value

    @model_validator(mode="after")
    def validate_dates(self) -> "TradeCreate":
        """Ensure closed_at is strictly after opened_at when both are provided.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If ``closed_at`` is before ``opened_at``.
        """
        if self.closed_at is not None and self.closed_at < self.opened_at:
            raise ValueError("closed_at must be after opened_at")
        return self


class TradeCreateRequest(BaseModel):
    """Public API request body for creating a new trade.

    This is the schema exposed in the OpenAPI documentation and used as the
    FastAPI request body type in route handlers.  It does **not** contain
    ``user_id`` — that field is injected by the handler from the authenticated
    user and merged into :class:`TradeCreate` before service calls.

    Attributes:
        symbol: Ticker symbol (e.g. ``"AAPL"``).
        direction: Long or short.
        asset_class: Asset class of the instrument.
        quantity: Number of units / contracts traded.
        entry_price: Execution price at open.
        exit_price: Execution price at close (omit for open trades).
        stop_loss: Optional stop-loss price.
        take_profit: Optional take-profit price.
        opened_at: Timezone-aware UTC timestamp of position open.
        closed_at: Timezone-aware UTC timestamp of position close.
        pnl: Realised PnL.
        commission: Total commission paid; defaults to zero.
        notes: Free-text notes.
        currency: ISO-4217 currency code (e.g. ``"USD"``).
        pnl_eur: Realised P&L in EUR (optional, set by broker importers or manually).
        account_id: Optional broker account UUID.
        playbook_id: Optional playbook UUID.
        tag_ids: List of tag UUIDs to attach.
        commission: Total commission paid; defaults to zero.
        notes: Free-text notes.
        account_id: Optional broker account UUID.
        playbook_id: Optional playbook UUID.
        tag_ids: List of tag UUIDs to attach.
    """

    symbol: str = Field(
        ...,
        min_length=SYMBOL_MIN_LENGTH,
        max_length=SYMBOL_MAX_LENGTH,
        description=(
            "Ticker symbol of the traded instrument. "
            "Maximum 30 characters (e.g. 'AAPL', 'EURUSD', 'CHTR  251003P00240000')."
        ),
        examples=["AAPL", "EURUSD", "BTCUSDT", "ES"],
    )
    direction: Direction = Field(
        ...,
        description=(
            "Trade direction — 'LONG' for a buy position, 'SHORT' for a sell position."
        ),
        examples=["LONG", "SHORT"],
    )
    asset_class: AssetClass = Field(
        ...,
        description=(
            "Asset class of the traded instrument. "
            "One of: EQUITY, OPTION, FUTURE, FOREX, CRYPTO."
        ),
        examples=["EQUITY", "FOREX", "CRYPTO"],
    )
    quantity: Decimal = Field(
        ...,
        ge=Decimal("0"),
        description=(
            "Number of units, shares, or contracts traded. Must be greater than zero."
        ),
        examples=["100", "1.5", "0.01"],
    )
    entry_price: Decimal = Field(
        ...,
        ge=Decimal("0"),
        description=(
            "Execution price at which the position was opened. "
            "Must be greater than zero."
        ),
        examples=["150.25", "1.0823", "42350.00"],
    )
    exit_price: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        description=(
            "Execution price at which the position was closed. "
            "Omit or set to null for trades that are still open."
        ),
        examples=["155.00", "1.0901", None],
    )
    stop_loss: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        description=(
            "Stop-loss price level for the trade. "
            "Omit or set to null if no stop-loss was set."
        ),
        examples=["148.00", "1.0780", None],
    )
    take_profit: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        description=(
            "Take-profit price level for the trade. "
            "Omit or set to null if no take-profit was set."
        ),
        examples=["158.00", "1.0950", None],
    )
    opened_at: datetime = Field(
        ...,
        description=(
            "Timezone-aware UTC timestamp of when the position was opened. "
            "Naive datetimes (without timezone info) are rejected."
        ),
        examples=["2024-03-15T09:30:00Z", "2024-03-15T09:30:00+00:00"],
    )
    closed_at: datetime | None = Field(
        default=None,
        description=(
            "Timezone-aware UTC timestamp of when the position was closed. "
            "Omit or set to null for trades that are still open. "
            "Naive datetimes are rejected."
        ),
        examples=["2024-03-15T15:45:00Z", None],
    )
    pnl: Decimal | None = Field(
        default=None,
        description=(
            "Realised profit or loss for this trade in account currency. "
            "Can be supplied manually; automated computation is planned "
            "for a later iteration. Null for open trades."
        ),
        examples=["475.00", "-120.50", None],
    )
    net_pnl: Decimal | None = Field(
        default=None,
        description=(
            "Realised net profit or loss for this trade in account currency. "
            "Null for open trades."
        ),
        examples=["473.50", "-123.70", None],
    )
    commission: Decimal = Field(
        default=Decimal("0"),
        ge=Decimal("0"),
        description="Total commission paid for this trade. Defaults to zero.",
        examples=["1.50", "3.20", "0"],
    )
    notes: str | None = Field(
        default=None,
        max_length=NOTES_MAX_LENGTH,
        description=(
            "Free-text notes attached to this trade, e.g. trade rationale, "
            "emotional state, or post-trade review."
        ),
        examples=["Breakout above 50-day MA. Tight stop below consolidation.", None],
    )
    tradingview_link: str | None = Field(
        default=None,
        description="Optional link to a TradingView chart for this trade.",
        examples=["https://www.tradingview.com/chart/...", None],
    )
    screenshots: list[str] | None = Field(
        default_factory=list,
        description="List of screenshot URLs for this trade.",
        examples=[["https://example.com/screenshot1.png"], []],
    )
    currency: str | None = Field(
        default=None,
        min_length=3,
        max_length=3,
        description=(
            "ISO-4217 currency code of the trade (e.g. 'USD'). "
            "Set automatically by broker importers; can also be set manually."
        ),
        examples=["USD", None],
    )
    pnl_eur: Decimal | None = Field(
        default=None,
        description=(
            "Realised P&L converted to EUR. Set automatically by broker importers "
            "at the official Bundesbank daily rate; can also be set manually."
        ),
        examples=["432.50", "-98.20", None],
    )
    net_pnl_eur: Decimal | None = Field(
        default=None,
        description=(
            "Realised net P&L converted to EUR. Set automatically by broker importers "
            "at the official Bundesbank daily rate; can also be set manually."
        ),
        examples=["430.50", "-100.20", None],
    )
    account_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "UUID of the broker account this trade belongs to. "
            "Omit to create an unassigned trade."
        ),
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6", None],
    )
    playbook_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "UUID of the playbook (strategy) to associate with this trade. "
            "Omit or set to null for no playbook."
        ),
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6", None],
    )
    tag_ids: list[uuid.UUID] = Field(
        default_factory=list,
        description=(
            "List of tag UUIDs to attach to this trade. "
            "All UUIDs must belong to the authenticated user."
        ),
        examples=[["3fa85f64-5717-4562-b3fc-2c963f66afa6"], []],
    )

    @field_validator("opened_at", "closed_at", mode="after")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        """Reject naive datetimes — all timestamps must carry timezone info.

        Args:
            value: Parsed datetime value (already coerced from string by Pydantic).

        Returns:
            The original value unchanged if it is timezone-aware or None.

        Raises:
            ValueError: If the supplied ``datetime`` has no ``tzinfo``.
        """
        if value is not None and value.tzinfo is None:
            raise ValueError("Datetime must be timezone-aware (include UTC offset).")
        return value

    @model_validator(mode="after")
    def validate_dates(self) -> "TradeCreateRequest":
        """Ensure closed_at is strictly after opened_at when both are provided.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If ``closed_at`` is before ``opened_at``.
        """
        if self.closed_at is not None and self.closed_at < self.opened_at:
            raise ValueError("closed_at must be after opened_at")
        return self

    def to_trade_create(self, user_id: uuid.UUID) -> "TradeCreate":
        """Convert this request to an internal :class:`TradeCreate` with user_id set.

        Args:
            user_id: UUID of the authenticated user, injected by the route handler.

        Returns:
            A :class:`TradeCreate` ready for use by the service layer.
        """
        return TradeCreate(
            user_id=user_id,
            **self.model_dump(),
        )


class TradeUpdate(BaseModel):
    """Request schema for partially updating an existing trade.

    All fields are optional.  Pydantic v2 distinguishes between a field
    that was **omitted** (not in ``model_fields_set``) and one that was
    **explicitly set to** ``null`` (present in ``model_fields_set`` with
    value ``None``).  The repository layer uses
    ``model_dump(exclude_unset=True)`` so that:

    - Omitting a field → the DB column is left unchanged.
    - Sending ``"field": null`` → the DB column is set to ``NULL``.

    This is particularly important for nullable optional fields such as
    ``stop_loss`` and ``take_profit``.

    Attributes:
        symbol: Updated ticker symbol.
        direction: Updated direction.
        asset_class: Updated asset class.
        quantity: Updated quantity.
        entry_price: Updated entry price.
        exit_price: Updated exit price (set to ``None`` to re-open).
        stop_loss: Updated stop-loss level; ``null`` clears it.
        take_profit: Updated take-profit level; ``null`` clears it.
        opened_at: Updated open timestamp.
        closed_at: Updated close timestamp.
        pnl: Updated PnL value.
        commission: Updated commission value.
        notes: Updated notes.
    """

    symbol: str | None = Field(
        default=None,
        min_length=SYMBOL_MIN_LENGTH,
        max_length=SYMBOL_MAX_LENGTH,
        description=(
            "Updated ticker symbol. Maximum 30 characters. Omit to leave unchanged."
        ),
        examples=["AAPL", "EURUSD", None],
    )
    direction: Direction | None = Field(
        default=None,
        description=(
            "Updated trade direction — 'LONG' or 'SHORT'. Omit to leave unchanged."
        ),
        examples=["LONG", "SHORT", None],
    )
    asset_class: AssetClass | None = Field(
        default=None,
        description=("Updated asset class of the instrument. Omit to leave unchanged."),
        examples=["EQUITY", "CRYPTO", None],
    )
    quantity: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        description=(
            "Updated number of units or contracts. Must be greater than zero. "
            "Omit to leave unchanged."
        ),
        examples=["200", "0.5", None],
    )
    entry_price: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        description=(
            "Updated entry execution price. Must be greater than zero. "
            "Omit to leave unchanged."
        ),
        examples=["151.00", "1.0830", None],
    )
    exit_price: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        description=(
            "Updated exit execution price. Supply this field (along with "
            "`closed_at` and `pnl`) to close an open trade. "
            "Omit to leave unchanged."
        ),
        examples=["156.50", "1.0910", None],
    )
    stop_loss: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        description=(
            "Updated stop-loss price level. Set to null to remove the stop-loss. "
            "Omit to leave unchanged. "
            "Pydantic v2 tracks whether this field was explicitly set via "
            "``model_fields_set``; the repository uses "
            "``model_dump(exclude_unset=True)`` "
            "so that an explicit ``null`` clears the field while omitting it "
            "leaves it unchanged."
        ),
        examples=["149.00", None],
    )
    take_profit: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        description=(
            "Updated take-profit price level. Set to null to remove the take-profit. "
            "Omit to leave unchanged. "
            "Pydantic v2 tracks whether this field was explicitly set via "
            "``model_fields_set``; the repository uses "
            "``model_dump(exclude_unset=True)`` "
            "so that an explicit ``null`` clears the field while omitting it "
            "leaves it unchanged."
        ),
        examples=["160.00", None],
    )
    opened_at: datetime | None = Field(
        default=None,
        description=(
            "Updated timezone-aware UTC timestamp for position open. "
            "Naive datetimes are rejected. Omit to leave unchanged."
        ),
        examples=["2024-03-15T09:31:00Z", None],
    )
    closed_at: datetime | None = Field(
        default=None,
        description=(
            "Updated timezone-aware UTC timestamp for position close. "
            "Naive datetimes are rejected. Omit to leave unchanged."
        ),
        examples=["2024-03-15T16:00:00Z", None],
    )
    pnl: Decimal | None = Field(
        default=None,
        description=(
            "Updated realised profit or loss in account currency. "
            "Omit to leave unchanged."
        ),
        examples=["530.00", "-85.00", None],
    )
    net_pnl: Decimal | None = Field(
        default=None,
        description=(
            "Updated realised net profit or loss in account currency. "
            "Omit to leave unchanged."
        ),
        examples=["528.00", "-87.00", None],
    )
    commission: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        description=(
            "Updated total commission paid. Must be zero or greater. "
            "Omit to leave unchanged."
        ),
        examples=["2.00", "0", None],
    )
    notes: str | None = Field(
        default=None,
        max_length=NOTES_MAX_LENGTH,
        description=(
            "Updated free-text notes. Set to null to clear existing notes. "
            "Omit to leave unchanged."
        ),
        examples=["Revised entry — slippage on open.", None],
    )
    tradingview_link: str | None = Field(
        default=None,
        description=(
            "Updated TradingView link. Set to null to clear. Omit to leave unchanged."
        ),
        examples=["https://www.tradingview.com/chart/...", None],
    )
    screenshots: list[str] | None = Field(
        default=None,
        description=(
            "Updated list of screenshot URLs. Set to null to clear. "
            "Omit to leave unchanged."
        ),
        examples=[["https://example.com/screenshot1.png"], None],
    )
    playbook_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "Updated playbook UUID. Omit to leave unchanged. "
            "Set to null to detach the current playbook."
        ),
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6", None],
    )
    tag_ids: list[uuid.UUID] | None = Field(
        default=None,
        description=(
            "Replacement list of tag UUIDs. When supplied, the existing tags "
            "are replaced with this set. Omit to leave tags unchanged. "
            "Pass an empty list ``[]`` to remove all tags."
        ),
        examples=[["3fa85f64-5717-4562-b3fc-2c963f66afa6"], [], None],
    )

    @field_validator("opened_at", "closed_at", mode="before")
    @classmethod
    def require_timezone(cls, value: object) -> object:
        """Reject naive datetimes — all timestamps must carry timezone info.

        Args:
            value: Raw datetime value from the request payload.

        Returns:
            The original value unchanged if it is timezone-aware.

        Raises:
            ValueError: If the supplied ``datetime`` has no ``tzinfo``.
        """
        if isinstance(value, datetime) and value.tzinfo is None:
            raise ValueError("Datetime must be timezone-aware (include UTC offset).")
        return value


class TradeRead(BaseModel):
    """Response schema returned for a single trade.

    Attributes:
        id: UUID primary key.
        symbol: Ticker symbol.
        direction: Long or short.
        asset_class: Asset class.
        quantity: Position size.
        entry_price: Open execution price.
        exit_price: Close execution price (``None`` if still open).
        stop_loss: Stop-loss price (``None`` if not set).
        take_profit: Take-profit price (``None`` if not set).
        opened_at: Timestamp of position open.
        closed_at: Timestamp of position close (``None`` if still open).
        pnl: Realised PnL (``None`` if not yet closed / calculated).
        commission: Commission paid.
        notes: Free-text notes.
        playbook_id: Optional UUID of the associated playbook.
        tags: List of tags attached to this trade.
        trade_notes: List of psychological / review notes on this trade.
        created_at: Row-creation timestamp.
        updated_at: Row-last-updated timestamp.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(
        ...,
        description=(
            "Unique identifier (UUID v4) assigned to this trade by the database."
        ),
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    )
    symbol: str = Field(
        ...,
        description="Ticker symbol of the traded instrument.",
        examples=["AAPL", "EURUSD", "BTCUSDT"],
    )
    direction: Direction = Field(
        ...,
        description=(
            "Trade direction: 'LONG' for a buy position, 'SHORT' for a sell position."
        ),
        examples=["LONG", "SHORT"],
    )
    asset_class: AssetClass = Field(
        ...,
        description="Asset class of the traded instrument.",
        examples=["EQUITY", "FOREX", "CRYPTO"],
    )
    quantity: Decimal = Field(
        ...,
        description="Number of units, shares, or contracts traded.",
        examples=["100", "1.5", "0.01"],
    )
    entry_price: Decimal = Field(
        ...,
        description="Execution price at which the position was opened.",
        examples=["150.25", "1.0823", "42350.00"],
    )
    exit_price: Decimal | None = Field(
        ...,
        description=(
            "Execution price at which the position was closed. "
            "Null if the trade is still open."
        ),
        examples=["155.00", "1.0901", None],
    )
    stop_loss: Decimal | None = Field(
        ...,
        description="Stop-loss price level. Null if no stop-loss was set.",
        examples=["148.00", "1.0780", None],
    )
    take_profit: Decimal | None = Field(
        ...,
        description="Take-profit price level. Null if no take-profit was set.",
        examples=["158.00", "1.0950", None],
    )
    opened_at: datetime = Field(
        ...,
        description="Timezone-aware UTC timestamp of when the position was opened.",
        examples=["2024-03-15T09:30:00Z"],
    )
    closed_at: datetime | None = Field(
        ...,
        description=(
            "Timezone-aware UTC timestamp of when the position was closed. "
            "Null if the trade is still open."
        ),
        examples=["2024-03-15T15:45:00Z", None],
    )
    pnl: Decimal | None = Field(
        ...,
        description=(
            "Realised profit or loss in account currency. "
            "Null if the trade is still open or PnL has not been calculated."
        ),
        examples=["475.00", "-120.50", None],
    )
    net_pnl: Decimal | None = Field(
        default=None,
        description=(
            "Realised net profit or loss in account currency. "
            "Null if the trade is still open or PnL has not been calculated."
        ),
        examples=["473.50", "-123.70", None],
    )
    commission: Decimal = Field(
        ...,
        description="Total commission paid for this trade.",
        examples=["1.50", "3.20", "0"],
    )
    notes: str | None = Field(
        ...,
        description=(
            "Free-text notes attached to this trade. Null if no notes were added."
        ),
        examples=["Breakout above 50-day MA.", None],
    )
    tradingview_link: str | None = Field(
        default=None,
        description="Optional link to a TradingView chart.",
        examples=["https://www.tradingview.com/chart/...", None],
    )
    screenshots: list[str] = Field(
        default_factory=list,
        description="List of screenshot URLs for this trade.",
        examples=[["https://example.com/screenshot1.png"]],
    )
    currency: str | None = Field(
        default=None,
        description=(
            "ISO-4217 currency code of the trade (e.g. 'USD'). "
            "Null for legacy trades imported before EUR-reporting was added."
        ),
        examples=["USD", None],
    )
    pnl_eur: Decimal | None = Field(
        default=None,
        description=(
            "Realised P&L converted to EUR at the official Bundesbank daily rate "
            "on the trade date. Null for open trades or when the rate is unavailable."
        ),
        examples=["432.50", "-98.20", None],
    )
    net_pnl_eur: Decimal | None = Field(
        default=None,
        description=(
            "Realised net P&L converted to EUR at the official Bundesbank daily rate "
            "on the trade date. Null for open trades or when the rate is unavailable."
        ),
        examples=["430.50", "-100.20", None],
    )
    playbook_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "UUID of the playbook associated with this trade. "
            "Null if no playbook is assigned."
        ),
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6", None],
    )
    playbook_name: str | None = Field(
        default=None,
        description=(
            "Name of the playbook associated with this trade, resolved from the "
            "joined playbook relationship. Null if no playbook is assigned."
        ),
        examples=["Breakout long", None],
    )
    account_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "UUID of the broker account this trade belongs to. "
            "Null if no account is assigned."
        ),
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6", None],
    )
    account_name: str | None = Field(
        default=None,
        description=(
            "Human-readable name of the broker account, resolved from the "
            "joined account relationship. Null if no account is assigned."
        ),
        examples=["Interactive Brokers Main", None],
    )
    account_type: str | None = Field(
        default=None,
        description=(
            "Type of the broker account (e.g. 'ibkr', 'schwab', 'manual'), "
            "resolved from the joined account relationship."
        ),
        examples=["ibkr", "schwab", "manual", None],
    )
    tags: list[TagRead] = Field(
        default_factory=list,
        description="Tags attached to this trade.",
    )
    trade_notes: list[TradeNoteRead] = Field(
        default_factory=list,
        description="Psychological and review notes attached to this trade.",
    )
    is_manually_edited: bool = Field(
        default=False,
        description=(
            "When True, this trade was manually corrected and will be "
            "skipped on subsequent broker re-imports."
        ),
        examples=[False, True],
    )
    created_at: datetime = Field(
        ...,
        description="UTC timestamp of when this record was inserted into the database.",
        examples=["2024-03-15T09:30:01Z"],
    )
    updated_at: datetime = Field(
        ...,
        description="UTC timestamp of the most recent update to this record.",
        examples=["2024-03-15T15:45:02Z"],
    )

    @model_validator(mode="before")
    @classmethod
    def _resolve_playbook_name(cls, data: Any) -> Any:
        """Populate ``playbook_name`` from the ORM ``playbook`` relationship.

        When constructing from an ORM instance (``from_attributes=True``), the
        ``playbook`` attribute may be an eagerly-loaded
        :class:`~app.models.playbook.Playbook` object.  This validator extracts
        its ``name`` so callers do not need to issue a separate query.

        Also populates ``account_name`` and ``account_type`` from the ORM
        ``account`` relationship when present.

        Args:
            data: Raw input data — either a dict or an ORM instance.

        Returns:
            The (possibly augmented) input data.
        """
        if not isinstance(data, dict):
            # Resolve playbook name.
            playbook = getattr(data, "playbook", None)
            if playbook is not None and getattr(data, "playbook_name", None) is None:
                with contextlib.suppress(Exception):
                    data.__dict__["playbook_name"] = playbook.name

            # Resolve account name + type.
            account = getattr(data, "account", None)
            if account is not None:
                if getattr(data, "account_name", None) is None:
                    with contextlib.suppress(Exception):
                        data.__dict__["account_name"] = account.name
                if getattr(data, "account_type", None) is None:
                    with contextlib.suppress(Exception):
                        raw_type = account.type
                        # AccountType is a StrEnum — .value gives the string
                        data.__dict__["account_type"] = (
                            raw_type.value
                            if hasattr(raw_type, "value")
                            else str(raw_type)
                        )
        return data


# ─── Filter / Sort schemas ────────────────────────────────────────────────────


class TradeFilterParams(BaseModel):
    """Query parameters for filtering the trade list.

    All fields are optional. When multiple filters are provided,
    they are combined with AND logic.

    Attributes:
        symbol: Case-insensitive partial match on symbol.
        direction: Filter by LONG or SHORT.
        asset_class: Filter by asset class.
        tag_ids: Filter by tag UUIDs.
        tag_filter_mode: AND or OR logic when multiple tag_ids are given.
        playbook_id: Filter by playbook UUID.
        opened_at_from: Filter trades opened at or after this datetime.
        opened_at_to: Filter trades opened at or before this datetime.
        pnl_positive: ``True`` for winners (pnl > 0), ``False`` for losers.
        status: ``'open'`` for trades without a close date, ``'closed'`` for
            trades that have been closed.
        account_id: Filter trades by broker account UUID.
        hour_of_day: Filter by UTC hour of ``opened_at`` (0–23).
        day_of_week: Filter by ISO day of week of ``opened_at``
            (0 = Monday, …, 6 = Sunday).
    """

    symbol: str | None = Field(
        default=None,
        description="Case-insensitive partial match on symbol",
    )
    direction: Direction | None = Field(
        default=None,
        description="Filter by LONG or SHORT",
    )
    asset_class: AssetClass | None = Field(
        default=None,
        description="Filter by asset class",
    )
    tag_ids: list[uuid.UUID] | None = Field(
        default=None,
        description="Filter by tag UUIDs",
    )
    tag_filter_mode: Literal["and", "or"] = Field(
        default="and",
        description="AND or OR logic for tag filter",
    )
    playbook_id: uuid.UUID | None = Field(
        default=None,
        description="Filter by playbook UUID",
    )
    opened_at_from: datetime | None = Field(
        default=None,
        description=("Filter trades opened at or after this datetime (timezone-aware)"),
    )
    opened_at_to: datetime | None = Field(
        default=None,
        description=(
            "Filter trades opened at or before this datetime (timezone-aware)"
        ),
    )
    closed_at_from: datetime | None = Field(
        default=None,
        description=("Filter trades closed at or after this datetime (timezone-aware)"),
    )
    closed_at_to: datetime | None = Field(
        default=None,
        description=(
            "Filter trades closed at or before this datetime (timezone-aware)"
        ),
    )
    pnl_positive: bool | None = Field(
        default=None,
        description="True = winners (pnl > 0), False = losers (pnl <= 0)",
    )
    status: Literal["open", "closed"] | None = Field(
        default=None,
        description=(
            "'open' = trades without a close date (closed_at IS NULL), "
            "'closed' = trades that have been closed (closed_at IS NOT NULL)."
        ),
    )
    account_id: uuid.UUID | None = Field(
        default=None,
        description="Filter trades by broker account UUID.",
    )
    hour_of_day: int | None = Field(
        default=None,
        ge=0,
        le=23,
        description="Filter trades by UTC hour of opened_at (0–23).",
    )
    day_of_week: int | None = Field(
        default=None,
        ge=0,
        le=6,
        description=(
            "Filter trades by ISO day of week of opened_at: "
            "0 = Monday, 1 = Tuesday, …, 6 = Sunday."
        ),
    )

    @field_validator(
        "opened_at_from",
        "opened_at_to",
        "closed_at_from",
        "closed_at_to",
        mode="before",
    )
    @classmethod
    def require_timezone(cls, value: object) -> object:
        """Reject naive datetimes — all timestamps must carry timezone info.

        Args:
            value: Raw datetime value from the request payload.

        Returns:
            The original value unchanged if it is timezone-aware or not a datetime.

        Raises:
            ValueError: If the supplied ``datetime`` has no ``tzinfo``.
        """
        if isinstance(value, datetime) and value.tzinfo is None:
            raise ValueError("Datetime must be timezone-aware (include UTC offset).")
        return value


class TradeSortField(StrEnum):
    """Sortable fields for the trade list."""

    symbol = "symbol"
    direction = "direction"
    asset_class = "asset_class"
    entry_price = "entry_price"
    exit_price = "exit_price"
    pnl = "pnl"
    quantity = "quantity"
    opened_at = "opened_at"
    closed_at = "closed_at"


class TradeSortParams(BaseModel):
    """Query parameters for sorting the trade list.

    Attributes:
        sort_by: The field to sort by. Defaults to ``opened_at``.
        sort_dir: Sort direction — ``"asc"`` or ``"desc"``. Defaults to ``"desc"``.
    """

    sort_by: TradeSortField = Field(
        default=TradeSortField.opened_at,
        description="Field to sort by",
    )
    sort_dir: Literal["asc", "desc"] = Field(
        default="desc",
        description="Sort direction",
    )


# ─── Bulk operation schemas ───────────────────────────────────────────────────


class BulkDeleteRequest(BaseModel):
    """Request body for bulk deletion of trades.

    Attributes:
        trade_ids: UUIDs of trades to delete (1–100).
    """

    trade_ids: list[uuid.UUID] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="UUIDs of trades to delete (1–100)",
    )


class BulkTagMode(StrEnum):
    """Mode for bulk tag assignment."""

    add = "add"
    remove = "remove"


class BulkAssignTagsRequest(BaseModel):
    """Request body for bulk tag assignment/removal.

    Attributes:
        trade_ids: UUIDs of trades to update.
        tag_ids: UUIDs of tags to add or remove.
        mode: ``'add'`` to add tags, ``'remove'`` to remove them.
    """

    trade_ids: list[uuid.UUID] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="UUIDs of trades to update",
    )
    tag_ids: list[uuid.UUID] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="UUIDs of tags to add or remove",
    )
    mode: BulkTagMode = Field(
        ...,
        description="'add' to add tags, 'remove' to remove them",
    )


class BulkAssignPlaybookRequest(BaseModel):
    """Request body for bulk playbook assignment.

    Attributes:
        trade_ids: UUIDs of trades to update.
        playbook_id: UUID of playbook to assign, or ``None`` to unassign.
    """

    trade_ids: list[uuid.UUID] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="UUIDs of trades to update",
    )
    playbook_id: uuid.UUID | None = Field(
        default=None,
        description="UUID of playbook to assign, or null to unassign",
    )


class BulkDeleteResponse(BaseModel):
    """Response for bulk delete operations.

    Attributes:
        deleted_count: Number of trades actually deleted.
    """

    deleted_count: int = Field(
        ...,
        description="Number of trades actually deleted",
    )


class BulkUpdateResponse(BaseModel):
    """Response for bulk update operations.

    Attributes:
        updated_count: Number of trades actually updated.
    """

    updated_count: int = Field(
        ...,
        description="Number of trades actually updated",
    )
