"""SQLAlchemy ORM model for the ``portfolios`` table."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import CURRENCY_LENGTH
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.user import User


class Portfolio(Base):
    """ORM representation of a user-owned portfolio."""

    __tablename__ = "portfolios"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    base_currency: Mapped[str] = mapped_column(
        String(CURRENCY_LENGTH),
        nullable=False,
    )
    color_hex: Mapped[str | None] = mapped_column(
        String(7),
        nullable=True,
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

    user: Mapped["User"] = relationship("User", back_populates="portfolios")
    accounts: Mapped[list["Account"]] = relationship(
        "Account",
        back_populates="portfolio",
    )

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_portfolios_user_name"),
        CheckConstraint(
            "color_hex IS NULL OR color_hex ~ '^#[0-9A-Fa-f]{6}$'",
            name="ck_portfolios_color_hex",
        ),
        Index("ix_portfolios_user_id", "user_id"),
    )
