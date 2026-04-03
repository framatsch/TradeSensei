"""Pydantic DTOs for BrokerRawTransaction request and response shapes."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import (
    CURRENCY_LENGTH,
    NUMERIC_SCALE,
    SYMBOL_MAX_LENGTH,
)
from app.models.trade import AssetClass, Direction

_BROKER_TYPE_MAX_LENGTH: int = 50
_EXEC_ID_MAX_LENGTH: int = 200
_CONID_MAX_LENGTH: int = 50


class BrokerRawTransactionCreate(BaseModel):
    """Schema for creating a new
    :class:`~app.models.broker_raw_transaction.BrokerRawTransaction`.

    This DTO is produced by broker parsers (e.g.
    :class:`~app.utils.parsers.ibkr_xml.IBKRXMLParser`)
    and consumed by the import service to persist the raw execution data before
    the logical layer is generated.

    Attributes:
        id: Composite broker execution ID (``"{broker_type}:{transaction_id}"``).
            Must be unique per user — used as the idempotency key on re-imports.
        user_id: UUID of the owning user.  Injected by the import service, not
            supplied by parsers.
        account_id: Optional UUID of the associated account.  Injected by the
            import service, not supplied by parsers.
        broker_type: Short broker identifier (e.g. ``"ibkr"``).
        symbol: Ticker symbol as provided by the broker.
        conid: Broker contract identifier (e.g. IBKR conid), or ``None``.
        asset_class: Asset class of the traded instrument.
        direction: Buy (LONG) or sell (SHORT) side of the execution.
        quantity: Absolute execution quantity (always positive).
        price: Execution price per unit.
        commission: Absolute commission charged for this execution.
        executed_at: Timestamp of the execution in UTC.
        pnl: Broker-reported realised P&L for this execution (``None`` for
            opening legs).
        currency: ISO-4217 currency code (e.g. ``"USD"``).
        multiplier: Contract multiplier (default 1 for equities).
        raw_data: Full dict of raw XML/CSV attributes as provided by the broker
            source.
    """

    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(
        ...,
        max_length=_EXEC_ID_MAX_LENGTH,
        description=(
            "Composite broker execution ID: "
            "'{user_id}:{broker_type}:{transaction_id}'. "
            "Used as idempotency key for re-imports."
        ),
    )
    user_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "UUID of the owning user.  Injected by the import service before "
            "persistence; not populated by parsers."
        ),
    )
    account_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "Optional UUID of the associated account.  Injected by the import "
            "service before persistence; not populated by parsers."
        ),
    )
    broker_type: str = Field(
        ...,
        max_length=_BROKER_TYPE_MAX_LENGTH,
        description="Short broker identifier, e.g. 'ibkr' or 'schwab'.",
    )
    symbol: str = Field(..., max_length=SYMBOL_MAX_LENGTH)
    conid: str | None = Field(
        default=None,
        max_length=_CONID_MAX_LENGTH,
        description="Broker contract identifier (IBKR conid).",
    )
    asset_class: AssetClass
    direction: Direction
    quantity: Decimal = Field(
        ...,
        ge=Decimal("0"),
        decimal_places=NUMERIC_SCALE,
        description="Absolute execution quantity (always positive).",
    )
    price: Decimal = Field(
        ...,
        ge=Decimal("0"),
        decimal_places=NUMERIC_SCALE,
        description="Execution price per unit.",
    )
    commission: Decimal = Field(
        default=Decimal("0"),
        ge=Decimal("0"),
        decimal_places=NUMERIC_SCALE,
        description="Absolute commission charged for this execution.",
    )
    executed_at: datetime = Field(
        ...,
        description="Timestamp of the execution (UTC).",
    )
    pnl: Decimal | None = Field(
        default=None,
        decimal_places=NUMERIC_SCALE,
        description="Broker-reported realised P&L (None for opening legs).",
    )
    currency: str | None = Field(
        default=None,
        max_length=CURRENCY_LENGTH,
        description="ISO-4217 currency code (e.g. 'USD').",
    )
    multiplier: int = Field(
        default=1,
        ge=1,
        description="Contract multiplier (1 for equities, >1 for futures/options).",
    )
    raw_data: dict[str, object] = Field(
        default_factory=dict,
        description="Full raw attribute dictionary from the broker source file.",
    )
