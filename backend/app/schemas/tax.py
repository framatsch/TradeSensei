"""Pydantic DTOs for tax reporting endpoints.

Provides schemas for the annual tax summary endpoint, which groups
realised P&L in EUR by asset class according to German §20 EStG categories.
"""

import uuid
from decimal import Decimal

from pydantic import BaseModel, Field

_ZERO = Decimal("0")


class TaxCategoryBlock(BaseModel):
    """P&L summary for one §20 EStG tax category (equities or derivatives).

    Attributes:
        gains_eur: Sum of all positive ``pnl_eur`` values in this category.
        losses_eur: Sum of all negative ``pnl_eur`` values in this category
            (always <= 0).
        net_eur: ``gains_eur + losses_eur`` — the net result for this category.
        trade_count: Number of closed trades with a non-null ``pnl_eur`` in
            this category.
    """

    gains_eur: Decimal = Field(
        ...,
        description=(
            "Total realised gains in EUR for this category (sum of positive pnl_eur). "
            "Always >= 0."
        ),
        examples=["1200.50"],
    )
    losses_eur: Decimal = Field(
        ...,
        description=(
            "Total realised losses in EUR for this category (sum of negative pnl_eur). "
            "Always <= 0."
        ),
        examples=["-300.00"],
    )
    net_eur: Decimal = Field(
        ...,
        description="Net P&L in EUR for this category (gains_eur + losses_eur).",
        examples=["900.50"],
    )
    trade_count: int = Field(
        ...,
        description="Number of closed trades with a known pnl_eur in this category.",
        examples=[45],
    )


class AccountTaxSummary(BaseModel):
    """Annual tax summary for a specific account."""

    account_id: uuid.UUID | None = Field(
        ...,
        description=(
            "The account ID. Can be null if trades are not linked to an account."
        ),
    )
    account_name: str | None = Field(
        ...,
        description="The name of the account.",
        examples=["Interactive Brokers Main"],
    )
    equities: TaxCategoryBlock = Field(
        ...,
        description=(
            "§20 Abs. 2 Nr. 1 EStG — realised gains and losses from "
            "equity trades for this account."
        ),
    )
    derivatives: TaxCategoryBlock = Field(
        ...,
        description=(
            "§20 Abs. 2 Nr. 3 EStG — realised gains and losses from derivatives "
            "and other instruments for this account."
        ),
    )
    total_net_eur: Decimal = Field(
        ...,
        description="Combined net P&L in EUR across both categories for this account.",
        examples=["600.50"],
    )
    trades_missing_eur: int = Field(
        default=0,
        description=(
            "Number of closed trades in this account/year where pnl_eur could not be "
            "determined."
        ),
        examples=[0, 3],
    )
    dividends_eur: Decimal = Field(
        default=_ZERO,
        description=(
            "Total dividends received in EUR for this account/year "
            "(§20 Abs. 1 Nr. 1 EStG)."
        ),
        examples=["120.50"],
    )
    withholding_tax_eur: Decimal = Field(
        default=_ZERO,
        description=(
            "Total withholding tax (Quellensteuer) paid in EUR for this account/year. "
            "Always <= 0."
        ),
        examples=["-18.08"],
    )
    interest_eur: Decimal = Field(
        default=_ZERO,
        description=(
            "Total interest income in EUR for this account/year "
            "(§20 Abs. 1 Nr. 7 EStG)."
        ),
        examples=["3.20"],
    )


class TaxAnnualSummary(BaseModel):
    """Annual tax summary for German Anlage KAP reporting.

    Splits realised P&L in EUR into two §20 EStG categories:

    - **equities**: §20 Abs. 2 Nr. 1 EStG — ``AssetClass.EQUITY`` trades.
    - **derivatives**: §20 Abs. 2 Nr. 3 EStG — all other asset classes
      (``OPTION``, ``FUTURE``, ``FOREX``, ``CRYPTO``).

    Attributes:
        year: Calendar year this summary covers.
        equities: P&L block for equity (stock) trades.
        derivatives: P&L block for derivatives / other instruments.
        total_net_eur: Combined net P&L across both categories.
        trades_missing_eur: Number of closed trades in this year where
            ``pnl_eur`` is NULL (could not be converted to EUR).
        dividends_eur: Total dividends in EUR across all accounts.
        withholding_tax_eur: Total withholding tax in EUR across all accounts.
        interest_eur: Total interest income in EUR across all accounts.
    """

    year: int = Field(
        ...,
        description="Calendar year this summary covers.",
        examples=[2025],
    )
    equities: TaxCategoryBlock = Field(
        ...,
        description=(
            "§20 Abs. 2 Nr. 1 EStG — realised gains and losses from equity trades."
        ),
    )
    derivatives: TaxCategoryBlock = Field(
        ...,
        description=(
            "§20 Abs. 2 Nr. 3 EStG — realised gains and losses from derivatives "
            "and other instruments (options, futures, forex, crypto)."
        ),
    )
    total_net_eur: Decimal = Field(
        ...,
        description="Combined net P&L in EUR across both categories.",
        examples=["600.50"],
    )
    trades_missing_eur: int = Field(
        default=0,
        description=(
            "Number of closed trades in this year where pnl_eur could not be "
            "determined (exchange rate was unavailable at import time)."
        ),
        examples=[0, 3],
    )
    dividends_eur: Decimal = Field(
        default=_ZERO,
        description=(
            "Total dividends received in EUR across all accounts for this year."
        ),
        examples=["120.50"],
    )
    withholding_tax_eur: Decimal = Field(
        default=_ZERO,
        description=(
            "Total withholding tax (Quellensteuer) paid in EUR across all accounts "
            "for this year. Always <= 0."
        ),
        examples=["-18.08"],
    )
    interest_eur: Decimal = Field(
        default=_ZERO,
        description="Total interest income in EUR across all accounts for this year.",
        examples=["3.20"],
    )
    accounts: list[AccountTaxSummary] = Field(
        default_factory=list,
        description="Detailed tax summaries broken down by individual accounts.",
    )
