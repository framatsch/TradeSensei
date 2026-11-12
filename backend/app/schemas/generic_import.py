"""Public, versioned DTOs for broker-neutral execution files."""

from datetime import UTC, datetime, timedelta
from datetime import date as date_
from decimal import Decimal
from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, BaseModel, BeforeValidator, ConfigDict, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

from app.core.constants import (
    GENERIC_CONTRACT_MAX_LENGTH,
    GENERIC_FORMAT,
    GENERIC_FUTURE_HOURS,
    GENERIC_ID_MAX_LENGTH,
    NUMERIC_PRECISION,
    NUMERIC_SCALE,
    SYMBOL_MAX_LENGTH,
)


def _decimal_input(value: object) -> object:
    """Reject binary floats and booleans before Decimal conversion."""
    if isinstance(value, (float, bool)):
        raise PydanticCustomError("decimal_type", "Invalid decimal representation")
    return value


Number = Annotated[Decimal, BeforeValidator(_decimal_input), Field(allow_inf_nan=False, decimal_places=NUMERIC_SCALE, max_digits=NUMERIC_PRECISION)]
Identifier = Annotated[str, Field(min_length=1, max_length=GENERIC_ID_MAX_LENGTH)]
ContractIdentifier = Annotated[str, Field(min_length=1, max_length=GENERIC_CONTRACT_MAX_LENGTH)]


class GenericOptionV1(BaseModel):
    """Option contract details; symbol is supplied by the execution."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)
    strike: Number = Field(
        gt=Decimal("0"), description="Positive option strike price; decimal string or losslessly parsed JSON number.", examples=["580", "590.5"]
    )
    expiry: date_ = Field(description="Option expiration date (YYYY-MM-DD).", examples=["2026-12-18"])
    right: Literal["C", "P"] = Field(description="C for call, P for put.", examples=["C", "P"])


class GenericExecutionV1(BaseModel):
    """One execution (fill), not an aggregated position."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)
    external_id: Identifier | None = Field(
        default=None,
        description=(
            "Stable unique per-fill broker ID, trimmed and scoped to the target account. Supply on every execution or omit on every execution; duplicates "
            "within a file are rejected. Omission selects fingerprint identity."
        ),
        examples=["fill-1001", None],
    )
    executed_at: AwareDatetime = Field(
        description="RFC 3339 execution timestamp with Z or explicit UTC offset; normalized to UTC and limited to 24 hours in the future.",
        examples=["2026-01-02T14:30:00Z", "2026-01-02T09:30:00-05:00"],
    )
    symbol: str = Field(
        min_length=1,
        max_length=SYMBOL_MAX_LENGTH,
        description=(
            "Ticker normalized to uppercase; options use the underlying ticker. Futures without contract_id should include the contract month in the symbol."
        ),
        examples=["AAPL", "SPY", "ESZ6"],
    )
    asset_class: Literal["EQUITY", "OPTION", "FUTURE", "FOREX", "CRYPTO"] = Field(description="Instrument asset class.", examples=["EQUITY", "OPTION"])
    side: Literal["BUY", "SELL"] = Field(description="Execution buy/sell side, not the position's long/short direction.", examples=["BUY", "SELL"])
    position_effect: Literal["OPEN", "CLOSE", "CLOSE_OPEN"] | None = Field(
        default=None,
        description="Optional opening/closing intent; CLOSE_OPEN denotes a position flip. Omit when unknown; FIFO matching still applies.",
        examples=["OPEN", "CLOSE", "CLOSE_OPEN", None],
    )
    quantity: Number = Field(
        gt=Decimal("0"), description="Positive absolute fill quantity; decimal string or losslessly parsed JSON number.", examples=["1", "0.125"]
    )
    price: Number = Field(
        ge=Decimal("0"),
        description="Nonnegative per-unit price, before applying the contract multiplier; decimal string or losslessly parsed JSON number.",
        examples=["100", "0.1"],
    )
    commission: Number = Field(
        default=Decimal("0"),
        ge=Decimal("0"),
        description="Absolute nonnegative total fees for this fill in the execution currency; defaults to zero.",
        examples=["0", "1.25"],
    )
    currency: str = Field(pattern=r"^[A-Z]{3}$", description="Three uppercase ISO 4217 letters.", examples=["USD", "EUR"])
    multiplier: int | None = Field(
        default=None,
        ge=1,
        strict=True,
        description="Positive integer contract multiplier; required for OPTION and FUTURE. Omission for other asset classes is interpreted as one.",
        examples=[100, 50, 1],
    )
    order_id: Identifier | None = Field(
        default=None,
        description="Groups fills or legs of one order for combo detection; distinct from per-fill external_id and not used for deduplication.",
        examples=["order-100", None],
    )
    contract_id: ContractIdentifier | None = Field(
        default=None,
        description=(
            "Optional broker contract identifier. When absent, option identity is derived from underlying, expiry, right and strike; other instruments use "
            "their symbol."
        ),
        examples=["123456789", None],
    )
    option: GenericOptionV1 | None = Field(
        default=None,
        description="Required for OPTION executions and forbidden for every other asset class.",
        examples=[{"strike": "580", "expiry": "2026-12-18", "right": "C"}, None],
    )
    realized_pnl: Number | None = Field(
        default=None,
        description="Optional signed broker-reported realized P&L in the execution currency, informational and excluded from fingerprint identity.",
        examples=["25.50", "-10", None],
    )

    @field_validator("symbol")
    @classmethod
    def _uppercase_symbol(cls, value: str) -> str:
        return value.upper()

    @field_validator("executed_at", mode="before")
    @classmethod
    def _timestamp_string(cls, value: object) -> object:
        if not isinstance(value, (str, datetime)):
            raise PydanticCustomError("timestamp_format", "An offset-aware RFC 3339 timestamp is required")
        return value

    @field_validator("executed_at")
    @classmethod
    def _utc_timestamp(cls, value: datetime) -> datetime:
        value = value.astimezone(UTC)
        if value > datetime.now(UTC) + timedelta(hours=GENERIC_FUTURE_HOURS):
            raise PydanticCustomError("timestamp_future", "Execution timestamp exceeds the allowed future window")
        return value

    @model_validator(mode="after")
    def _contract_requirements(self) -> Self:
        if (self.asset_class == "OPTION") != (self.option is not None):
            raise PydanticCustomError("option_requirement", "Option details must be present exactly for options")
        if self.asset_class in ("OPTION", "FUTURE") and self.multiplier is None:
            raise PydanticCustomError("multiplier_required", "Contract multiplier is required")
        return self


class GenericSplitV1(BaseModel):
    """An insert-only stock split declaration."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)
    type: Literal["SPLIT"] = Field(description="Corporate action type, SPLIT only.", examples=["SPLIT"])
    symbol: str = Field(min_length=1, max_length=SYMBOL_MAX_LENGTH, description="Affected ticker, normalized to uppercase.", examples=["AAPL"])
    date: date_ = Field(description="Effective date (YYYY-MM-DD).", examples=["2026-05-01"])
    ratio: Number = Field(
        gt=Decimal("0"),
        description=(
            "Shares after divided by shares before; 2 means a 2-for-1 split, 0.1 means a reverse split. Existing differing ratios are preserved with a warning."
        ),
        examples=["2", "0.1"],
    )
    old_contract_id: ContractIdentifier | None = Field(default=None, description="Optional prior contract ID.", examples=["123456789", None])
    new_contract_id: ContractIdentifier | None = Field(default=None, description="Optional replacement contract ID.", examples=["987654321", None])

    @field_validator("symbol")
    @classmethod
    def _uppercase_symbol(cls, value: str) -> str:
        return value.upper()


class GenericExecutionDocumentV1(BaseModel):
    """Trade Sensei Execution Format v1 JSON envelope."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)
    format: Literal["tradesensei.executions"] = Field(description="Required constant format marker.", examples=["tradesensei.executions"])
    version: str = Field(pattern=r"^1\.[0-9]+$", description="Supported format version (1.x); other major versions are rejected.", examples=["1.0"])
    source: str | None = Field(
        default=None,
        max_length=GENERIC_ID_MAX_LENGTH,
        description="Informational source, never used for identity.",
        examples=["Broker export conversion", None],
    )
    executions: list[GenericExecutionV1] = Field(
        min_length=1,
        description=(
            "Nonempty list of fills, not aggregated trades. Validation is all-or-nothing; IDs must be unique and either present on all fills or absent on all "
            "fills."
        ),
        examples=[
            [
                {
                    "external_id": "fill-1001",
                    "executed_at": "2026-01-02T14:30:00Z",
                    "symbol": "AAPL",
                    "asset_class": "EQUITY",
                    "side": "BUY",
                    "quantity": "1",
                    "price": "100",
                    "currency": "USD",
                }
            ]
        ],
    )
    corporate_actions: list[GenericSplitV1] = Field(
        default_factory=list,
        description="Optional insert-only splits (JSON only); cash movements, dividends, interest and transfers are not supported.",
        examples=[[], [{"type": "SPLIT", "symbol": "AAPL", "date": "2026-05-01", "ratio": "2"}]],
    )

    @model_validator(mode="before")
    @classmethod
    def _marker_first(cls, value: object) -> object:
        if not isinstance(value, dict) or value.get("format") != GENERIC_FORMAT:
            raise PydanticCustomError("format_marker", "Required format marker is missing or invalid")
        return value


class GenericValidationIssue(BaseModel):
    """Safe row-level error that never contains submitted values."""

    row: int | None = Field(
        default=None,
        description="Zero-based JSON array index or one-based CSV data row (excluding the header); null for envelope or account-strategy errors.",
        examples=[0, 1, None],
    )
    field: str = Field(description="Field path only, without submitted values.", examples=["executed_at", "external_id"])
    code: str = Field(description="Machine-readable validation error code.", examples=["duplicate_external_id", "mixed_id_strategy", "id_strategy_mismatch"])
    message: str = Field(
        description="Value-free validation message; never echoes prices, quantities or P&L.", examples=["External IDs must be unique within a file"]
    )


class ImportPreviewResult(BaseModel):
    """Raw-level novelty preview; does not aggregate or persist."""

    detected_strategy: Literal["external_id", "fingerprint"] | None = Field(
        default=None, description="Identity strategy detected from the file; preview never locks the account strategy.", examples=["external_id", "fingerprint"]
    )
    recorded_strategy: Literal["external_id", "fingerprint"] | None = Field(
        default=None,
        description="Strategy locked by the account's first successful import; null before that import or after clearing all account trades.",
        examples=["external_id", None],
    )
    strategy_conflict: bool = Field(
        default=False,
        description="True when detected and recorded strategies differ. Preview still returns HTTP 200, but upload rejects this file with HTTP 422.",
        examples=[False, True],
    )
    total: int = Field(default=0, description="Total validated execution fills in the file; this is not an aggregated trade count.", examples=[10])
    new: int = Field(default=0, description="Execution identities not yet present in the target account; total minus already_imported.", examples=[7])
    already_imported: int = Field(
        default=0, description="Execution identities already present, including suppressed or previously deleted records.", examples=[3]
    )
    suppressed: int = Field(
        default=0, description="Subset of already_imported whose raw transactions are suppressed; these remain excluded from upload.", examples=[1, 0]
    )
    new_splits: int = Field(default=0, description="Split declarations without an existing split for the user, symbol and date.", examples=[1, 0])
    conflicting_splits: int = Field(
        default=0, description="Split declarations whose ratio differs from an existing split; upload preserves the stored ratio and warns.", examples=[1, 0]
    )
    warnings: list[str] = Field(
        default_factory=list,
        description=(
            "Nonfatal format or split-conflict warnings. Fingerprint ordinals can diverge when overlapping exports contain different counts of identical "
            "fills; inspect novelty counts before confirming."
        ),
        examples=[[], ["split_conflict: existing split ratio preserved"]],
    )
    errors: list[GenericValidationIssue] = Field(
        default_factory=list,
        description=(
            "Empty for successful previews. Invalid files instead return HTTP 422 with a detail array of row-level issues, capped at 200, not a success "
            "envelope."
        ),
        examples=[[]],
    )


class GenericFormatSchema(BaseModel):
    """JSON Schema object, not an execution document."""

    model_config = ConfigDict(extra="allow")
    title: str = Field(description="Title of the published execution-document JSON Schema.", examples=["GenericExecutionDocumentV1"])
    type: Literal["object"] = Field(description="JSON Schema root instance type; describes an object, not a sample execution document.", examples=["object"])
    properties: dict[str, object] = Field(
        description="JSON Schema definitions of envelope fields. Nested execution, option and split schemas are included in the top-level $defs extension.",
        examples=[{"format": {"const": "tradesensei.executions", "type": "string"}}],
    )
    required: list[str] = Field(
        description="Envelope fields required by the published format. Other JSON Schema keywords, including $defs and additionalProperties, are preserved.",
        examples=[["format", "version", "executions"]],
    )
