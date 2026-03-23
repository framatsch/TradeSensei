"""Pydantic DTOs for Account request and response shapes."""

import uuid
from decimal import Decimal
from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from app.core.constants import (
    ACCOUNT_NAME_MAX_LENGTH,
    ACCOUNT_NAME_MIN_LENGTH,
    ACCOUNT_NUMBER_MAX_LENGTH,
    CURRENCY_LENGTH,
)
from app.models.account import AccountType

# ── Import/sync settings per account ─────────────────────────────────────────

FlexFromDatePreset = Literal["ytd", "custom"]


class AccountSettings(BaseModel):
    """Per-account import and sync preferences.

    These settings are stored as a JSONB blob on the ``accounts`` row and
    are loaded alongside the account on every read.

    Attributes:
        sync_days: Number of past days to fetch when using the broker API
            sync endpoint.  Defaults to ``30``.
        flex_from_date_preset: Controls the Flex import date-range mode.
            ``"ytd"`` always starts from January 1st of the current year;
            ``"custom"`` uses the explicit ``flex_custom_from_date`` value.
        flex_custom_from_date: Explicit start date (``YYYYMMDD``) used when
            ``flex_from_date_preset`` is ``"custom"``.  ``None`` otherwise.
    """

    sync_days: int = Field(
        default=30,
        ge=1,
        le=365,
        description=(
            "Number of past days to pull via broker API sync. Must be between 1–365."
        ),
        examples=[7, 30, 90, 180, 365],
    )
    flex_from_date_preset: FlexFromDatePreset = Field(
        default="ytd",
        description=(
            "Controls the Flex import date-range mode: "
            "'ytd' = January 1st of the current year, "
            "'custom' = the explicit flex_custom_from_date value."
        ),
        examples=["ytd", "custom"],
    )
    flex_custom_from_date: str | None = Field(
        default=None,
        description=(
            "Explicit Flex import start date in YYYYMMDD format. "
            "Only used when flex_from_date_preset is 'custom'."
        ),
        examples=["20250101", None],
    )

    @field_validator("flex_custom_from_date")
    @classmethod
    def validate_date_format(cls, v: str | None) -> str | None:
        """Validate that the date string matches YYYYMMDD format."""
        if v is None:
            return v
        if len(v) != 8 or not v.isdigit():
            raise ValueError("flex_custom_from_date must be in YYYYMMDD format.")
        return v


class AccountCreate(BaseModel):
    """Request schema for creating a new trading account.

    Attributes:
        name: Human-readable account name (e.g. "Interactive Brokers Main").
        account_number: Optional broker account number (e.g. "U1234567").
        type: Account/broker type. Defaults to ``MANUAL``.
        currency: ISO-4217 currency code; defaults to ``"USD"``.
        properties: Optional mapping of broker credential keys to plaintext
            values.  The service layer encrypts each value before storage.
            Pass ``null`` or omit to create an account without credentials.
        settings: Optional per-account import/sync settings. Defaults apply
            when omitted.
    """

    name: str = Field(
        ...,
        min_length=ACCOUNT_NAME_MIN_LENGTH,
        max_length=ACCOUNT_NAME_MAX_LENGTH,
        description="Human-readable account label (e.g. 'Interactive Brokers Main').",
        examples=["Interactive Brokers Main", "Schwab Cash Account"],
    )
    account_number: str | None = Field(
        default=None,
        max_length=ACCOUNT_NUMBER_MAX_LENGTH,
        description="Optional broker account number (e.g. 'U1234567').",
        examples=["U1234567", None],
    )
    type: AccountType = Field(
        default=AccountType.MANUAL,
        description=(
            "Account/broker type. Use 'schwab' for Charles Schwab, "
            "'ibkr' for Interactive Brokers, or 'manual' for a manual account."
        ),
        examples=["manual", "schwab", "ibkr"],
    )
    currency: str = Field(
        default="USD",
        min_length=CURRENCY_LENGTH,
        max_length=CURRENCY_LENGTH,
        description="ISO-4217 currency code for the account (exactly 3 characters).",
        examples=["USD", "EUR", "GBP"],
    )
    properties: dict[str, str] | None = Field(
        default=None,
        description=(
            "Optional map of broker credential keys to plaintext values "
            "(e.g. {'SCHWAB_APP_KEY': '...', 'SCHWAB_APP_SECRET': '...'}).  "
            "Values are encrypted at rest. Pass null or omit to skip."
        ),
        examples=[
            {"SCHWAB_APP_KEY": "abc123", "SCHWAB_APP_SECRET": "xyz789"},
            None,
        ],
    )
    settings: AccountSettings | None = Field(
        default=None,
        description="Optional per-account import/sync settings.",
    )


class AccountUpdate(BaseModel):
    """Request schema for partially updating a trading account.

    All fields are optional — only supplied fields are written.

    Attributes:
        name: Updated account name.
        account_number: Updated broker account number. Pass ``null`` to clear.
        type: Updated account/broker type.
        currency: Updated currency code.
        is_active: Updated active flag.
        properties: Optional map of broker credential keys to updated
            plaintext values.  Existing properties not included here are
            left unchanged (merge semantics).
        settings: Optional updated import/sync settings. Merges with existing
            settings (partial update semantics).
    """

    name: str | None = Field(
        default=None,
        min_length=ACCOUNT_NAME_MIN_LENGTH,
        max_length=ACCOUNT_NAME_MAX_LENGTH,
        description="Updated account label. Omit to leave unchanged.",
        examples=["IBKR Futures Account", None],
    )
    account_number: str | None = Field(
        default=None,
        max_length=ACCOUNT_NUMBER_MAX_LENGTH,
        description="Updated broker account number. Pass null to clear.",
        examples=["U7654321", None],
    )
    type: AccountType | None = Field(
        default=None,
        description="Updated account/broker type. Omit to leave unchanged.",
        examples=["schwab", None],
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
    properties: dict[str, str] | None = Field(
        default=None,
        description=(
            "Optional map of broker credential keys to updated plaintext values. "
            "Upserts each supplied key-value pair; keys not listed here are unchanged."
        ),
        examples=[
            {"SCHWAB_APP_KEY": "new-key-value"},
            None,
        ],
    )
    settings: AccountSettings | None = Field(
        default=None,
        description="Optional updated import/sync settings. Omit to leave unchanged.",
    )


class AccountRead(BaseModel):
    """Response schema for a single trading account.

    Attributes:
        id: UUID primary key.
        user_id: UUID of the owning user.
        name: Account label.
        account_number: Optional broker account number.
        type: Account/broker type.
        currency: ISO-4217 currency code.
        is_active: Whether the account is active.
        settings: Per-account import/sync preferences. Returns defaults if
            no settings have been saved yet.
        created_at: UTC timestamp of account creation.
        has_api_keys: ``True`` if the account has any stored broker
            credentials (computed by the service layer, never read directly
            from the ORM).
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
    account_number: str | None = Field(
        default=None,
        description="Optional broker account number (e.g. 'U1234567').",
        examples=["U1234567", None],
    )
    type: AccountType = Field(
        ...,
        description="Account/broker type.",
        examples=["manual", "schwab", "ibkr"],
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
    settings: AccountSettings = Field(
        default_factory=AccountSettings,
        description=(
            "Per-account import/sync settings. Returns defaults if not yet configured."
        ),
        validate_default=True,
    )

    @field_validator("settings", mode="before")
    @classmethod
    def validate_settings(cls, v: Any) -> Any:
        """Ensure settings is never None; return default AccountSettings instead."""
        if v is None:
            return {}
        return v

    created_at: AwareDatetime = Field(
        ...,
        description="UTC timestamp of account creation.",
        examples=["2024-03-15T09:30:00Z"],
    )
    has_api_keys: bool = Field(
        default=False,
        description=(
            "True if the account has at least one stored broker credential. "
            "Computed by the service layer."
        ),
        examples=[True, False],
    )


class AccountMetrics(BaseModel):
    """Aggregate metrics for a single trading account.

    Attributes:
        total_dividends: Total dividends received in this account (in EUR).
        total_withholding_tax: Total withholding tax paid in this account (in EUR).
    """

    total_dividends: Decimal = Field(
        default=Decimal("0.0"),
        description="Total dividends received across this account.",
        examples=["150.50"],
    )
    total_withholding_tax: Decimal = Field(
        default=Decimal("0.0"),
        description="Total withholding tax paid across this account.",
        examples=["-22.50"],
    )
