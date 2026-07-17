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

"""Pydantic schemas for logical execution request and response payloads."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.trade import AssetClass, Direction

# Valid origin values for type annotation
ExecutionOrigin = Literal["imported", "manual", "merged", "split"]


class LogicalExecutionBase(BaseModel):
    """Shared properties for all LogicalExecution schemas."""

    direction: Direction
    quantity: Decimal = Field(gt=0, description="Execution quantity (absolute, always positive)")
    price: Decimal = Field(ge=0, description="Execution price per unit")
    commission: Decimal = Field(default=Decimal("0.0"), description="Commission for this execution leg")
    executed_at: datetime = Field(
        description="Timestamp of the execution (UTC)",
        json_schema_extra={"format": "date-time-tz"},
    )
    pnl: Decimal | None = Field(default=None, description="Broker-reported realised P&L (None for opening legs)")

    @field_validator("executed_at", mode="after")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        """Reject naive datetimes."""
        if value.tzinfo is None:
            raise ValueError("executed_at must be timezone-aware (include UTC offset).")
        return value


class LogicalExecutionCreate(LogicalExecutionBase):
    """Schema for creating a manual LogicalExecution.

    Note: ``origin`` is always set to ``'manual'`` by the service layer —
    it is not accepted from the API consumer.
    """

    asset_class: AssetClass | None = Field(
        default=None,
        description=("Optional per-leg asset class override for COMBO trades. Ignored for non-COMBO parent trades."),
    )
    multiplier: int | None = Field(
        default=None,
        gt=0,
        description=("Optional per-leg multiplier override for COMBO trades. Ignored for non-COMBO parent trades."),
    )


class LogicalExecutionUpdate(BaseModel):
    """Schema for updating a LogicalExecution.

    Note: ``origin``, ``deleted``, and ``user_modified`` are not patchable
    by the API consumer.  ``user_modified`` is set automatically by the
    service when patching an imported execution.
    """

    direction: Direction | None = None
    quantity: Decimal | None = Field(default=None, gt=0)
    price: Decimal | None = Field(default=None, ge=0)
    commission: Decimal | None = None
    executed_at: datetime | None = None
    pnl: Decimal | None = None

    @field_validator("executed_at", mode="after")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        """Reject naive datetimes when executed_at is provided."""
        if value is not None and value.tzinfo is None:
            raise ValueError("executed_at must be timezone-aware (include UTC offset).")
        return value


class ReassignExecutionRequest(BaseModel):
    """Request payload for moving an execution to another trade."""

    target_trade_id: uuid.UUID


class ReassignExecutionResponse(BaseModel):
    """Response payload returned after reassigning an execution."""

    execution: "LogicalExecutionRead"
    message: str


class SplitExecutionRequest(BaseModel):
    """Request payload for splitting one execution into two.

    Both resulting executions share the same ``trade_id`` and ``origin='split'``.
    The original execution is soft-deleted (``deleted=true``).

    Attributes:
        quantity_a: Quantity of the first resulting execution.
        quantity_b: Quantity of the second resulting execution.
            Must sum to the original execution's quantity.
        price_a: Price for the first execution (defaults to original price).
        price_b: Price for the second execution (defaults to original price).
        executed_at_a: Timestamp for the first execution (defaults to original).
        executed_at_b: Timestamp for the second execution (defaults to original).
    """

    quantity_a: Decimal = Field(gt=0, description="Quantity of the first resulting execution")
    quantity_b: Decimal = Field(gt=0, description="Quantity of the second resulting execution")
    price_a: Decimal | None = Field(default=None, ge=0, description="Price for the first execution")
    price_b: Decimal | None = Field(default=None, ge=0, description="Price for the second execution")
    executed_at_a: datetime | None = Field(default=None, description="Timestamp for the first execution (UTC)")
    executed_at_b: datetime | None = Field(default=None, description="Timestamp for the second execution (UTC)")

    @field_validator("executed_at_a", "executed_at_b", mode="after")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        """Reject naive datetimes when timestamps are provided."""
        if value is not None and value.tzinfo is None:
            raise ValueError("executed_at must be timezone-aware (include UTC offset).")
        return value


class SplitExecutionResponse(BaseModel):
    """Response payload returned after splitting an execution.

    Attributes:
        execution_a: First resulting split execution.
        execution_b: Second resulting split execution.
        original: The original execution (now soft-deleted).
    """

    execution_a: "LogicalExecutionRead"
    execution_b: "LogicalExecutionRead"
    original: "LogicalExecutionRead"


class MergeExecutionsRequest(BaseModel):
    """Request payload for merging two or more executions into one.

    All source executions must belong to the same trade, have the same
    direction and symbol, and must not already be deleted.

    The primary execution (``primary_id``) sets the ``parent_id`` for the
    merged result.

    Attributes:
        execution_ids: IDs of all executions to merge (must include at
            least 2 entries; ``primary_id`` must be one of them).
        primary_id: The execution whose metadata (price, executed_at) will
            be used as the base for the merged result.
        price: Override price for the merged execution.  Defaults to the
            weighted-average price of the source executions.
        executed_at: Override timestamp for the merged execution.  Defaults
            to the timestamp of the primary execution.
    """

    execution_ids: list[uuid.UUID] = Field(
        min_length=2,
        description="IDs of all executions to merge (at least 2 required).",
    )
    primary_id: uuid.UUID = Field(description=("The execution whose metadata is used as the base. Must be included in execution_ids."))
    price: Decimal | None = Field(
        default=None,
        ge=0,
        description=("Override price for the merged execution. When omitted, the weighted-average price is used."),
    )
    executed_at: datetime | None = Field(
        default=None,
        description=("Override timestamp for the merged execution (UTC). When omitted, the primary execution's timestamp is used."),
    )

    @field_validator("executed_at", mode="after")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        """Reject naive datetimes when executed_at is provided."""
        if value is not None and value.tzinfo is None:
            raise ValueError("executed_at must be timezone-aware (include UTC offset).")
        return value


class MergeExecutionsResponse(BaseModel):
    """Response payload returned after merging executions.

    Attributes:
        merged: The newly created merged execution.
        sources: The original executions (now soft-deleted).
    """

    merged: "LogicalExecutionRead"
    sources: list["LogicalExecutionRead"]


class LogicalExecutionRead(LogicalExecutionBase):
    """Schema for reading a LogicalExecution."""

    model_config = ConfigDict(from_attributes=True)

    price: Decimal = Field(ge=0, description="Split-adjusted execution price per unit for chart alignment")
    quantity: Decimal = Field(gt=0, description="Split-adjusted execution quantity for chart alignment")
    raw_price: Decimal | None = Field(
        default=None,
        ge=0,
        description="Original stored execution price per unit before split adjustment",
    )
    raw_quantity: Decimal | None = Field(
        default=None,
        gt=0,
        description="Original stored execution quantity before split adjustment",
    )

    id: uuid.UUID
    user_id: uuid.UUID
    account_id: uuid.UUID | None = None
    symbol: str
    conid: str | None = None
    asset_class: AssetClass
    pnl_eur: Decimal | None = None
    multiplier: int
    currency: str | None = None
    open_close: str | None = Field(
        default=None,
        description="Opening/closing indicator: 'O' (opening), 'C' (closing), or null (mixed/unknown/manual)",
    )
    origin: ExecutionOrigin = Field(description="Immutable provenance: imported | manual | merged | split")
    deleted: bool = Field(description="True when this execution has been soft-deleted")
    user_modified: bool = Field(description="True when the user has patched an imported execution")
    parent_id: uuid.UUID | None = Field(
        default=None,
        description="FK to original execution for split/merge lineage",
    )
    trade_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def fill_raw_defaults(self) -> Self:
        """Default raw fields to stored values when service did not enrich them."""
        if self.raw_price is None:
            self.raw_price = self.price
        if self.raw_quantity is None:
            self.raw_quantity = self.quantity
        return self
