"""Pydantic DTOs for Account request and response shapes."""

import uuid

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.core.constants import (
    ACCOUNT_NAME_MAX_LENGTH,
    ACCOUNT_NAME_MIN_LENGTH,
    CURRENCY_LENGTH,
)


class AccountCreate(BaseModel):
    """Request schema for creating a new trading account.

    Attributes:
        name: Human-readable account name (e.g. "Interactive Brokers Main").
        broker: Optional broker identifier (e.g. "IBKR", "Schwab").
        currency: ISO-4217 currency code; defaults to ``"USD"``.
    """

    name: str = Field(
        ...,
        min_length=ACCOUNT_NAME_MIN_LENGTH,
        max_length=ACCOUNT_NAME_MAX_LENGTH,
        description="Human-readable account label (e.g. 'Interactive Brokers Main').",
        examples=["Interactive Brokers Main", "Schwab Cash Account"],
    )
    broker: str | None = Field(
        default=None,
        max_length=50,
        description=(
            "Optional broker identifier (e.g. 'IBKR', 'Schwab', 'TD'). Omit if unknown."
        ),
        examples=["IBKR", "Schwab", None],
    )
    currency: str = Field(
        default="USD",
        min_length=CURRENCY_LENGTH,
        max_length=CURRENCY_LENGTH,
        description="ISO-4217 currency code for the account (exactly 3 characters).",
        examples=["USD", "EUR", "GBP"],
    )


class AccountUpdate(BaseModel):
    """Request schema for partially updating a trading account.

    All fields are optional — only supplied fields are written.

    Attributes:
        name: Updated account name.
        broker: Updated broker identifier.
        currency: Updated currency code.
        is_active: Updated active flag.
    """

    name: str | None = Field(
        default=None,
        min_length=ACCOUNT_NAME_MIN_LENGTH,
        max_length=ACCOUNT_NAME_MAX_LENGTH,
        description="Updated account label. Omit to leave unchanged.",
        examples=["IBKR Futures Account", None],
    )
    broker: str | None = Field(
        default=None,
        max_length=50,
        description="Updated broker identifier. Omit to leave unchanged.",
        examples=["IBKR", None],
    )
    currency: str | None = Field(
        default=None,
        min_length=CURRENCY_LENGTH,
        max_length=CURRENCY_LENGTH,
        description="Updated ISO-4217 currency code. Omit to leave unchanged.",
        examples=["EUR", None],
    )
    is_active: bool | None = Field(
        default=None,
        description="Updated active flag. Omit to leave unchanged.",
        examples=[False, None],
    )


class AccountRead(BaseModel):
    """Response schema for a single trading account.

    Attributes:
        id: UUID primary key.
        user_id: UUID of the owning user.
        name: Account label.
        broker: Broker identifier (``None`` if not set).
        currency: ISO-4217 currency code.
        is_active: Whether the account is active.
        created_at: UTC timestamp of account creation.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(
        ...,
        description="Unique account identifier (UUID v4).",
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    )
    user_id: uuid.UUID = Field(
        ...,
        description="UUID of the user who owns this account.",
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    )
    name: str = Field(
        ...,
        description="Human-readable account label.",
        examples=["Interactive Brokers Main"],
    )
    broker: str | None = Field(
        ...,
        description="Broker identifier, or null if not specified.",
        examples=["IBKR", None],
    )
    currency: str = Field(
        ...,
        description="ISO-4217 currency code for the account.",
        examples=["USD"],
    )
    is_active: bool = Field(
        ...,
        description="Whether this account is currently active.",
        examples=[True],
    )
    created_at: AwareDatetime = Field(
        ...,
        description="UTC timestamp of account creation.",
        examples=["2024-03-15T09:30:00Z"],
    )
