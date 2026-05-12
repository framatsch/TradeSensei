"""Association model between check-ins and taxonomy definitions."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.daily_checkin import DailyCheckin
    from app.models.taxonomy import Taxonomy


class CheckinTaxonomy(Base):
    """Assignment table between a check-in and a taxonomy definition."""

    __tablename__ = "checkin_taxonomies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    checkin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("daily_checkins.id", ondelete="CASCADE"),
        nullable=False,
    )
    taxonomy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("taxonomies.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    checkin: Mapped["DailyCheckin"] = relationship(
        "DailyCheckin",
        back_populates="taxonomy_assignments",
    )
    taxonomy: Mapped["Taxonomy"] = relationship(
        "Taxonomy",
        back_populates="checkin_assignments",
    )

    __table_args__ = (UniqueConstraint("checkin_id", "taxonomy_id", name="uq_checkin_taxonomy_pair"),)
