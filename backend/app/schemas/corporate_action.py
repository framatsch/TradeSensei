"""Pydantic DTOs for CorporateAction request and response shapes."""

import uuid
from datetime import date as date_
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.constants import SYMBOL_MAX_LENGTH

_CONID_MAX_LENGTH: int = 50
_RATIO_DESCRIPTION = (
    "Split ratio expressed as a Decimal. "
    "Greater than 1 for a forward split (e.g. 2.0 = 2:1 split). "
    "Less than 1 for a reverse split (e.g. 0.05 = 1:20 reverse split). "
    "Compute as after_shares / before_shares."
)


class CorporateActionCreate(BaseModel):
    """Internal schema for creating a new corporate action (used by service layer).

    The ``user_id`` field is injected by the route handler from the authenticated
    user — it is never supplied by an API client directly.

    Attributes:
        user_id: UUID of the owning user — injected by the route handler.
        symbol: Ticker symbol the action applies to (e.g. ``"OTLK"``).
        date: Calendar date on which the split took effect.
        ratio: Split ratio (after / before).  > 1 forward, < 1 reverse.
        old_conid: Optional broker contract ID before the split (IBKR-specific).
        new_conid: Optional broker contract ID after the split (IBKR-specific).
    """

    user_id: uuid.UUID | None = None
    symbol: str = Field(
        ...,
        min_length=1,
        max_length=SYMBOL_MAX_LENGTH,
        description="Ticker symbol the corporate action applies to (e.g. 'OTLK').",
        examples=["OTLK", "AAPL"],
    )
    date: date_ = Field(
        ...,
        description="Calendar date on which the split took effect (ISO 8601 date).",
        examples=["2023-05-01"],
    )
    ratio: Decimal = Field(
        ...,
        gt=Decimal("0"),
        description=_RATIO_DESCRIPTION,
        examples=["0.05", "2.0"],
    )
    old_conid: str | None = Field(
        default=None,
        max_length=_CONID_MAX_LENGTH,
        description=(
            "Broker contract ID before the split (IBKR conid). "
            "Required when the broker assigns a new instrument ID after the split."
        ),
        examples=["357194941", None],
    )
    new_conid: str | None = Field(
        default=None,
        max_length=_CONID_MAX_LENGTH,
        description=(
            "Broker contract ID after the split (IBKR conid). "
            "Required when the broker assigns a new instrument ID after the split."
        ),
        examples=["690184975", None],
    )

    @field_validator("ratio")
    @classmethod
    def ratio_must_be_positive(cls, v: Decimal) -> Decimal:
        """Reject non-positive ratios.

        Args:
            v: Parsed ratio value.

        Returns:
            The original value if valid.

        Raises:
            ValueError: If the ratio is zero or negative.
        """
        if v <= Decimal("0"):
            raise ValueError("ratio must be greater than 0")
        return v


class CorporateActionCreateRequest(BaseModel):
    """Public API request body for creating a new corporate action.

    The ``user_id`` field is NOT included here — it is injected by the route
    handler from the authenticated JWT claim.

    Attributes:
        symbol: Ticker symbol the action applies to.
        date: Calendar date on which the split took effect.
        ratio: Split ratio (after / before).
        old_conid: Optional broker contract ID before the split.
        new_conid: Optional broker contract ID after the split.
    """

    symbol: str = Field(
        ...,
        min_length=1,
        max_length=SYMBOL_MAX_LENGTH,
        description="Ticker symbol the corporate action applies to (e.g. 'OTLK').",
        examples=["OTLK", "AAPL"],
    )
    date: date_ = Field(
        ...,
        description="Calendar date on which the split took effect (ISO 8601 date).",
        examples=["2023-05-01"],
    )
    ratio: Decimal = Field(
        ...,
        gt=Decimal("0"),
        description=_RATIO_DESCRIPTION,
        examples=["0.05", "2.0"],
    )
    old_conid: str | None = Field(
        default=None,
        max_length=_CONID_MAX_LENGTH,
        description=(
            "Broker contract ID before the split (IBKR conid). "
            "Required when the broker assigns a new instrument ID after the split."
        ),
        examples=["357194941", None],
    )
    new_conid: str | None = Field(
        default=None,
        max_length=_CONID_MAX_LENGTH,
        description=(
            "Broker contract ID after the split (IBKR conid). "
            "Required when the broker assigns a new instrument ID after the split."
        ),
        examples=["690184975", None],
    )

    def to_corporate_action_create(self, user_id: uuid.UUID) -> "CorporateActionCreate":
        """Convert to internal :class:`CorporateActionCreate` with user_id injected.

        Args:
            user_id: UUID of the authenticated user, supplied by the route handler.

        Returns:
            A :class:`CorporateActionCreate` ready for the service layer.
        """
        return CorporateActionCreate(user_id=user_id, **self.model_dump())


class CorporateActionUpdate(BaseModel):
    """Request schema for partially updating an existing corporate action.

    All fields are optional.  Only supplied fields are updated in the DB.

    Attributes:
        symbol: Updated ticker symbol.
        date: Updated effective date.
        ratio: Updated split ratio.
        old_conid: Updated pre-split broker conid.  Set to null to clear.
        new_conid: Updated post-split broker conid.  Set to null to clear.
    """

    symbol: str | None = Field(
        default=None,
        min_length=1,
        max_length=SYMBOL_MAX_LENGTH,
        description="Updated ticker symbol. Omit to leave unchanged.",
        examples=["OTLK", None],
    )
    date: date_ | None = Field(
        default=None,
        description="Updated effective date. Omit to leave unchanged.",
        examples=["2023-05-02", None],
    )
    ratio: Decimal | None = Field(
        default=None,
        gt=Decimal("0"),
        description=(
            f"Updated split ratio. {_RATIO_DESCRIPTION}  Omit to leave unchanged."
        ),
        examples=["0.05", "2.0", None],
    )
    old_conid: str | None = Field(
        default=None,
        max_length=_CONID_MAX_LENGTH,
        description="Updated pre-split broker conid. Omit to leave unchanged.",
        examples=["357194941", None],
    )
    new_conid: str | None = Field(
        default=None,
        max_length=_CONID_MAX_LENGTH,
        description="Updated post-split broker conid. Omit to leave unchanged.",
        examples=["690184975", None],
    )


class CorporateActionRead(BaseModel):
    """Response schema returned for a single corporate action.

    Attributes:
        id: UUID primary key.
        user_id: UUID of the owning user.
        symbol: Ticker symbol.
        date: Effective date of the corporate action.
        ratio: Split ratio.
        old_conid: Broker contract ID before the split.
        new_conid: Broker contract ID after the split.
        created_at: Row creation timestamp.
        updated_at: Row last-updated timestamp.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(
        ...,
        description=(
            "Unique identifier (UUID v4) assigned to this record by the database."
        ),
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    )
    user_id: uuid.UUID = Field(
        ...,
        description="UUID of the user who owns this corporate action.",
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    )
    symbol: str = Field(
        ...,
        description="Ticker symbol the corporate action applies to.",
        examples=["OTLK", "AAPL"],
    )
    date: date_ = Field(
        ...,
        description="Calendar date on which the split took effect.",
        examples=["2023-05-01"],
    )
    ratio: Decimal = Field(
        ...,
        description=_RATIO_DESCRIPTION,
        examples=["0.05", "2.0"],
    )
    old_conid: str | None = Field(
        ...,
        description="Broker contract ID before the split. Null if not applicable.",
        examples=["357194941", None],
    )
    new_conid: str | None = Field(
        ...,
        description="Broker contract ID after the split. Null if not applicable.",
        examples=["690184975", None],
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
