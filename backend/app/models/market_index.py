"""SQLAlchemy ORM models for market index definitions."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
    Table,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.daily_checkin import DailyCheckin
    from app.models.user import User

checkin_market_indices = Table(
    "checkin_market_indices",
    Base.metadata,
    Column(
        "checkin_id",
        UUID(as_uuid=True),
        ForeignKey("daily_checkins.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "index_id",
        UUID(as_uuid=True),
        ForeignKey("market_index_definitions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class MarketIndexDefinition(Base):
    """User-scoped market index definitions."""

    __tablename__ = "market_index_definitions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    tradingview_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
        default=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (UniqueConstraint("user_id", "symbol", name="uq_market_index_user_symbol"),)

    user: Mapped["User"] = relationship("User", back_populates="market_indices")
    checkins: Mapped[list["DailyCheckin"]] = relationship(
        "DailyCheckin",
        secondary=checkin_market_indices,
        back_populates="target_indices",
    )
