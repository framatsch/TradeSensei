"""Pydantic DTOs for Trade request and response shapes."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.constants import NOTES_MAX_LENGTH, SYMBOL_MAX_LENGTH, SYMBOL_MIN_LENGTH
from app.models.trade import AssetClass, Direction
from app.schemas.note import TradeNoteRead
from app.schemas.tag import TagRead

# Sentinel singleton used to distinguish "field not provided" from "field set to None"

# Sentinel singleton used to distinguish "field not provided" from "field set to None"
_UNSET: object = object()


class TradeCreate(BaseModel):
    """Request schema for creating a new trade.

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
        pnl: Realised PnL (may be supplied manually; computed in later
            iterations).
        commission: Total commission paid; defaults to zero.
        notes: Free-text notes.
    """

    symbol: str = Field(
        ...,
        min_length=SYMBOL_MIN_LENGTH,
        max_length=SYMBOL_MAX_LENGTH,
        description=(
            "Ticker symbol of the traded instrument. "
            "Maximum 20 characters (e.g. 'AAPL', 'EURUSD', 'BTCUSDT')."
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
        gt=Decimal("0"),
        description=(
            "Number of units, shares, or contracts traded. Must be greater than zero."
        ),
        examples=["100", "1.5", "0.01"],
    )
    entry_price: Decimal = Field(
        ...,
        gt=Decimal("0"),
        description=(
            "Execution price at which the position was opened. "
            "Must be greater than zero."
        ),
        examples=["150.25", "1.0823", "42350.00"],
    )
    exit_price: Decimal | None = Field(
        default=None,
        gt=Decimal("0"),
        description=(
            "Execution price at which the position was closed. "
            "Omit or set to null for trades that are still open."
        ),
        examples=["155.00", "1.0901", None],
    )
    stop_loss: Decimal | None = Field(
        default=None,
        gt=Decimal("0"),
        description=(
            "Stop-loss price level for the trade. "
            "Omit or set to null if no stop-loss was set."
        ),
        examples=["148.00", "1.0780", None],
    )
    take_profit: Decimal | None = Field(
        default=None,
        gt=Decimal("0"),
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

    @model_validator(mode="after")
    def validate_dates(self) -> "TradeCreate":
        """Ensure closed_at is strictly after opened_at when both are provided.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If ``closed_at`` is not strictly after ``opened_at``.
        """
        if self.closed_at is not None and self.closed_at <= self.opened_at:
            raise ValueError("closed_at must be after opened_at")
        return self


class TradeUpdate(BaseModel):
    """Request schema for partially updating an existing trade.

    All fields are optional — only supplied fields will be written.

    Attributes:
        symbol: Updated ticker symbol.
        direction: Updated direction.
        asset_class: Updated asset class.
        quantity: Updated quantity.
        entry_price: Updated entry price.
        exit_price: Updated exit price (set to ``None`` to re-open).
        stop_loss: Updated stop-loss level.
        take_profit: Updated take-profit level.
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
            "Updated ticker symbol. Maximum 20 characters. Omit to leave unchanged."
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
        gt=Decimal("0"),
        description=(
            "Updated number of units or contracts. Must be greater than zero. "
            "Omit to leave unchanged."
        ),
        examples=["200", "0.5", None],
    )
    entry_price: Decimal | None = Field(
        default=None,
        gt=Decimal("0"),
        description=(
            "Updated entry execution price. Must be greater than zero. "
            "Omit to leave unchanged."
        ),
        examples=["151.00", "1.0830", None],
    )
    exit_price: Decimal | None = Field(
        default=None,
        gt=Decimal("0"),
        description=(
            "Updated exit execution price. Supply this field (along with "
            "`closed_at` and `pnl`) to close an open trade. "
            "Omit to leave unchanged."
        ),
        examples=["156.50", "1.0910", None],
    )
    stop_loss: Decimal | None = Field(
        default=None,
        gt=Decimal("0"),
        # NOTE: None means "not provided" (field omitted by client), not "set to null".
        # To support explicit null-clearing, a sentinel type is needed (future work).
        # TODO: Implement full sentinel pattern in a future iteration.
        description=(
            "Updated stop-loss price level. Set to null to remove the stop-loss. "
            "Omit to leave unchanged."
        ),
        examples=["149.00", None],
    )
    take_profit: Decimal | None = Field(
        default=None,
        gt=Decimal("0"),
        # NOTE: None means "not provided" (field omitted by client), not "set to null".
        # To support explicit null-clearing, a sentinel type is needed (future work).
        # TODO: Implement full sentinel pattern in a future iteration.
        description=(
            "Updated take-profit price level. Set to null to remove the take-profit. "
            "Omit to leave unchanged."
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
    playbook_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "UUID of the playbook associated with this trade. "
            "Null if no playbook is assigned."
        ),
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6", None],
    )
    tags: list[TagRead] = Field(
        default_factory=list,
        description="Tags attached to this trade.",
    )
    trade_notes: list[TradeNoteRead] = Field(
        default_factory=list,
        description="Psychological and review notes attached to this trade.",
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
