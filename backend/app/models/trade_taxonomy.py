"""Association model between trades and taxonomy definitions."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.taxonomy import Taxonomy
    from app.models.trade import Trade


class TradeTaxonomy(Base):
    """Assignment table between a trade and a taxonomy definition."""

    __tablename__ = "trade_taxonomies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    trade_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trades.id", ondelete="CASCADE"),
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

    trade: Mapped["Trade"] = relationship("Trade", back_populates="taxonomy_assignments")
    taxonomy: Mapped["Taxonomy"] = relationship("Taxonomy", back_populates="trade_assignments")

    __table_args__ = (UniqueConstraint("trade_id", "taxonomy_id", name="uq_trade_taxonomy_pair"),)
