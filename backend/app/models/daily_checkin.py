"""SQLAlchemy ORM models for daily check-ins and related definitions."""

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.market_index import checkin_market_indices

if TYPE_CHECKING:
    from app.models.checkin_annotation import CheckinAnnotation
    from app.models.checkin_taxonomy import CheckinTaxonomy
    from app.models.market_index import MarketIndexDefinition
    from app.models.user import User


class DailyCheckin(Base):
    """User-scoped daily check-in record."""

    __tablename__ = "daily_checkins"

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
    date: Mapped[date] = mapped_column(Date, nullable=False)
    market_phase: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    news_links: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        server_default="{}",
        default=list,
    )
    screenshot_urls: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        server_default="{}",
        default=list,
    )
    custom_metrics: Mapped[dict[str, bool | int] | None] = mapped_column(
        JSONB,
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

    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_daily_checkin_user_date"),)

    user: Mapped["User"] = relationship("User", back_populates="daily_checkins")
    target_indices: Mapped[list["MarketIndexDefinition"]] = relationship(
        "MarketIndexDefinition",
        secondary=checkin_market_indices,
        back_populates="checkins",
    )
    taxonomy_assignments: Mapped[list["CheckinTaxonomy"]] = relationship(
        "CheckinTaxonomy",
        back_populates="checkin",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )
    annotation_assignments: Mapped[list["CheckinAnnotation"]] = relationship(
        "CheckinAnnotation",
        back_populates="checkin",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )
