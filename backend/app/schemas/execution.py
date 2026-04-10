"""Pydantic schemas for logical execution request and response payloads."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.logical_execution import ExecutionStatus
from app.models.trade import AssetClass, Direction


class LogicalExecutionBase(BaseModel):
    """Shared properties for all LogicalExecution schemas."""

    direction: Direction
    quantity: Decimal = Field(
        gt=0, description="Execution quantity (absolute, always positive)"
    )
    price: Decimal = Field(ge=0, description="Execution price per unit")
    commission: Decimal = Field(
        default=Decimal("0.0"), description="Commission for this execution leg"
    )
    executed_at: datetime = Field(
        description="Timestamp of the execution (UTC)",
        json_schema_extra={"format": "date-time-tz"},
    )
    pnl: Decimal | None = Field(
        default=None, description="Broker-reported realised P&L (None for opening legs)"
    )

    @field_validator("executed_at", mode="after")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        """Reject naive datetimes."""
        if value.tzinfo is None:
            raise ValueError("executed_at must be timezone-aware (include UTC offset).")
        return value


class LogicalExecutionCreate(LogicalExecutionBase):
    """Schema for creating a manual LogicalExecution."""

    pass


class LogicalExecutionUpdate(BaseModel):
    """Schema for updating a LogicalExecution."""

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


class LogicalExecutionRead(LogicalExecutionBase):
    """Schema for reading a LogicalExecution."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    account_id: uuid.UUID | None = None
    symbol: str
    conid: str | None = None
    asset_class: AssetClass
    pnl_eur: Decimal | None = None
    multiplier: int
    currency: str | None = None
    status: ExecutionStatus
    trade_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
