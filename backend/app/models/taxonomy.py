"""SQLAlchemy ORM model for reusable metadata taxonomies."""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.checkin_taxonomy import CheckinTaxonomy
    from app.models.trade_taxonomy import TradeTaxonomy
    from app.models.user import User


class DefinitionScope(StrEnum):
    """Scope for where a definition can be assigned."""

    TRADES = "trades"
    CHECKINS = "checkins"
    BOTH = "both"


class Taxonomy(Base):
    """Reusable taxonomy definition assignable to trades and/or check-ins."""

    __tablename__ = "taxonomies"

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
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    scope: Mapped[str] = mapped_column(String(20), nullable=False)
    color_hex: Mapped[str] = mapped_column(String(7), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    icon_identifier: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_archived: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
        default=False,
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

    trade_assignments: Mapped[list["TradeTaxonomy"]] = relationship(
        "TradeTaxonomy",
        back_populates="taxonomy",
        passive_deletes=True,
    )
    checkin_assignments: Mapped[list["CheckinTaxonomy"]] = relationship(
        "CheckinTaxonomy",
        back_populates="taxonomy",
        passive_deletes=True,
    )
    user: Mapped["User"] = relationship("User")

    __table_args__ = (
        UniqueConstraint("user_id", "name", "scope", name="uq_taxonomies_user_name_scope"),
        Index("ix_taxonomies_user_id", "user_id"),
        Index("ix_taxonomies_scope", "scope"),
        Index("ix_taxonomies_archived", "is_archived"),
    )
