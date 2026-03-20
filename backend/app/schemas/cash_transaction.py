"""Pydantic DTOs for CashTransaction request and response shapes."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.constants import CURRENCY_LENGTH, SYMBOL_MAX_LENGTH
from app.models.cash_transaction import CashTransactionType


class CashTransactionCreate(BaseModel):
    """Internal schema for creating a new cash transaction.

    Attributes:
        account_id: UUID of the owning account.
        date: Timezone-aware UTC timestamp of the transaction.
        type: Category of the transaction.
        symbol: Optional symbol (e.g. for dividends).
        amount: Raw amount in the transaction's native currency.
        currency: ISO-4217 currency code.
        amount_eur: The amount converted to EUR at the Bundesbank daily rate.
        description: Optional free-text description.
    """

    account_id: uuid.UUID = Field(
        ...,
        description="UUID of the broker account this transaction belongs to.",
    )
    date: datetime = Field(
        ...,
        description="Timezone-aware UTC timestamp of the transaction.",
        examples=["2024-03-15T09:30:00Z", "2024-03-15T09:30:00+00:00"],
    )
    type: CashTransactionType = Field(
        ...,
        description="Type of the cash transaction.",
        examples=["DIVIDEND", "WITHHOLDING_TAX"],
    )
    symbol: str | None = Field(
        default=None,
        max_length=SYMBOL_MAX_LENGTH,
        description="Optional ticker symbol related to this transaction.",
        examples=["AAPL", None],
    )
    amount: Decimal = Field(
        ...,
        description="Raw amount in the transaction's native currency.",
        examples=["15.50", "-3.20"],
    )
    currency: str = Field(
        ...,
        min_length=3,
        max_length=CURRENCY_LENGTH,
        description="ISO-4217 currency code (e.g. 'USD').",
        examples=["USD", "EUR"],
    )
    amount_eur: Decimal | None = Field(
        default=None,
        description="Amount converted to EUR at the official Bundesbank daily rate.",
        examples=["14.20", "-2.95", None],
    )
    description: str | None = Field(
        default=None,
        description="Free-text description.",
        examples=["Microsoft Corporation Dividend", None],
    )

    @field_validator("date", mode="after")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        """Reject naive datetimes — must carry timezone info."""
        if value.tzinfo is None:
            raise ValueError("Datetime must be timezone-aware (include UTC offset).")
        return value


class CashTransactionCreateRequest(BaseModel):
    """Public API request body for creating a new cash transaction.

    The ``account_id`` will be provided in the path or injected.
    """

    date: datetime = Field(
        ...,
        description="Timezone-aware UTC timestamp of the transaction.",
        examples=["2024-03-15T09:30:00Z"],
    )
    type: CashTransactionType = Field(
        ...,
        description="Type of the cash transaction.",
        examples=["DIVIDEND", "FEE"],
    )
    symbol: str | None = Field(
        default=None,
        max_length=SYMBOL_MAX_LENGTH,
        description="Optional ticker symbol related to this transaction.",
        examples=["AAPL", None],
    )
    amount: Decimal = Field(
        ...,
        description="Raw amount in the transaction's native currency.",
        examples=["15.50", "-3.20"],
    )
    currency: str = Field(
        ...,
        min_length=3,
        max_length=CURRENCY_LENGTH,
        description="ISO-4217 currency code (e.g. 'USD').",
        examples=["USD"],
    )
    amount_eur: Decimal | None = Field(
        default=None,
        description="Amount converted to EUR. Leave null to auto-compute if possible.",
    )
    description: str | None = Field(
        default=None,
        description="Free-text description.",
    )

    @field_validator("date", mode="before")
    @classmethod
    def require_timezone(cls, value: object) -> object:
        if isinstance(value, datetime) and value.tzinfo is None:
            raise ValueError("Datetime must be timezone-aware (include UTC offset).")
        return value

    def to_cash_transaction_create(
        self, account_id: uuid.UUID
    ) -> CashTransactionCreate:
        """Convert this request to an internal schema."""
        return CashTransactionCreate(
            account_id=account_id,
            **self.model_dump(),
        )


class CashTransactionUpdate(BaseModel):
    """Request schema for updating a cash transaction."""

    date: datetime | None = Field(default=None)
    type: CashTransactionType | None = Field(default=None)
    symbol: str | None = Field(default=None, max_length=SYMBOL_MAX_LENGTH)
    amount: Decimal | None = Field(default=None)
    currency: str | None = Field(default=None, min_length=3, max_length=CURRENCY_LENGTH)
    amount_eur: Decimal | None = Field(default=None)
    description: str | None = Field(default=None)

    @field_validator("date", mode="before")
    @classmethod
    def require_timezone(cls, value: object) -> object:
        if isinstance(value, datetime) and value.tzinfo is None:
            raise ValueError("Datetime must be timezone-aware (include UTC offset).")
        return value


class CashTransactionRead(BaseModel):
    """Response schema for a single cash transaction."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    date: datetime
    type: CashTransactionType
    symbol: str | None
    amount: Decimal
    currency: str
    amount_eur: Decimal | None
    description: str | None
    created_at: datetime
    updated_at: datetime


class CashTransactionFilterParams(BaseModel):
    """Filter parameters for listing cash transactions."""

    type: CashTransactionType | None = Field(
        default=None,
        description="Filter by cash transaction type.",
    )
    symbol: str | None = Field(
        default=None,
        description="Filter by exact ticker symbol.",
    )
    from_date: datetime | None = Field(
        default=None,
        description="Return transactions on or after this date (UTC).",
    )
    to_date: datetime | None = Field(
        default=None,
        description="Return transactions on or before this date (UTC).",
    )
