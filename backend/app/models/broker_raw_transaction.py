"""SQLAlchemy ORM model for the ``broker_raw_transactions`` table.

This table is the immutable raw-data layer: every execution imported from a
broker is stored here exactly as received, without modification.  It acts as
the permanent audit log so that the application can always reconstruct the
original data, even after the logical layer has been manipulated.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import (
    CURRENCY_LENGTH,
    NUMERIC_PRECISION,
    NUMERIC_SCALE,
    SYMBOL_MAX_LENGTH,
)
from app.core.database import Base
from app.models.trade import AssetClass, Direction

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.logical_execution import LogicalExecution
    from app.models.user import User

BROKER_TYPE_MAX_LENGTH: int = 50
"""Maximum length for the broker type identifier string (e.g. 'ibkr')."""

EXEC_ID_MAX_LENGTH: int = 200
"""Maximum length for the broker execution ID string."""

CONID_MAX_LENGTH: int = 50
"""Maximum length for a broker contract identifier (conid)."""


class BrokerRawTransaction(Base):
    """Immutable record of a single broker execution as received from the source.

    This table is written once on import and never modified.  It stores the
    exact broker-provided data (quantities, prices, commission) together with
    the full raw attribute dictionary so that any field can be recovered later.

    The primary key is a composite broker execution ID of the form
    ``"{broker_type}:{transaction_id}"`` (e.g. ``"ibkr:2277515525"``).  This
    makes upserts idempotent: re-importing the same file never creates duplicate
    rows.

    Attributes:
        id: Composite broker execution ID (PK), e.g. ``"ibkr:2277515525"``.
        user_id: Foreign key to the owning :class:`~app.models.user.User`.
        account_id: Optional foreign key to the
            :class:`~app.models.account.Account`.
        broker_type: Short string identifying the broker (e.g. ``"ibkr"``).
        symbol: Ticker symbol as provided by the broker.
        conid: Broker contract identifier (IBKR conid), or ``None``.
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
        raw_data: Full dict of raw XML/CSV attributes as a JSONB blob.
        suppressed: When ``True``, this raw transaction is permanently excluded
            from all future imports (including fresh-start imports).
        logical_executions: Many-to-many relationship to
            :class:`~app.models.logical_execution.LogicalExecution` via the
            ``transaction_execution_mappings`` junction table.
        created_at: Row-creation timestamp set by the database.
    """

    __tablename__ = "broker_raw_transactions"

    id: Mapped[str] = mapped_column(
        String(EXEC_ID_MAX_LENGTH),
        primary_key=True,
        comment=("Composite broker execution ID: '{user_id}:{broker_type}:{transaction_id}'. Used as idempotency key for re-imports."),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    broker_type: Mapped[str] = mapped_column(
        String(BROKER_TYPE_MAX_LENGTH),
        nullable=False,
        comment="Short broker identifier, e.g. 'ibkr' or 'schwab'.",
    )
    symbol: Mapped[str] = mapped_column(
        String(SYMBOL_MAX_LENGTH),
        nullable=False,
    )
    conid: Mapped[str | None] = mapped_column(
        String(CONID_MAX_LENGTH),
        nullable=True,
        comment="Broker contract identifier (IBKR conid).",
    )
    asset_class: Mapped[AssetClass] = mapped_column(
        String(20),
        nullable=False,
    )
    direction: Mapped[Direction] = mapped_column(
        String(10),
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(NUMERIC_PRECISION, NUMERIC_SCALE),
        nullable=False,
        comment="Absolute execution quantity (always positive).",
    )
    price: Mapped[Decimal] = mapped_column(
        Numeric(NUMERIC_PRECISION, NUMERIC_SCALE),
        nullable=False,
        comment="Execution price per unit.",
    )
    commission: Mapped[Decimal] = mapped_column(
        Numeric(NUMERIC_PRECISION, NUMERIC_SCALE),
        nullable=False,
        server_default="0",
        comment="Absolute commission charged for this execution.",
    )
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Timestamp of the execution (UTC).",
    )
    pnl: Mapped[Decimal | None] = mapped_column(
        Numeric(NUMERIC_PRECISION, NUMERIC_SCALE),
        nullable=True,
        comment="Broker-reported realised P&L (None for opening legs).",
    )
    currency: Mapped[str | None] = mapped_column(
        String(CURRENCY_LENGTH),
        nullable=True,
        comment="ISO-4217 currency code (e.g. 'USD').",
    )
    multiplier: Mapped[int] = mapped_column(
        nullable=False,
        server_default="1",
        comment="Contract multiplier (1 for equities, >1 for futures/options).",
    )
    raw_data: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        server_default="{}",
        comment="Full raw attribute dictionary from the broker source file.",
    )
    suppressed: Mapped[bool] = mapped_column(
        Boolean(),
        nullable=False,
        server_default="false",
        comment=("When True, this raw transaction is permanently excluded from all future imports (including fresh-start imports)."),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_brt_user_id", "user_id"),
        Index("ix_brt_account_id", "account_id"),
        Index("ix_brt_symbol", "symbol"),
        Index("ix_brt_executed_at", "executed_at"),
        Index("ix_brt_conid", "conid"),
        Index("ix_brt_broker_type", "broker_type"),
        Index("ix_brt_suppressed", "suppressed"),
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="broker_raw_transactions",
    )
    account: Mapped[Optional["Account"]] = relationship(
        "Account",
        back_populates="broker_raw_transactions",
    )
    logical_executions: Mapped[list["LogicalExecution"]] = relationship(
        "LogicalExecution",
        secondary="transaction_execution_mappings",
        back_populates="raw_transactions",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """Return a debug string for this raw transaction.

        Returns:
            A string with id, symbol, direction, and quantity.
        """
        return f"<BrokerRawTransaction id={self.id!r} symbol={self.symbol!r} direction={self.direction} qty={self.quantity}>"
