"""SQLAlchemy ORM model for the ``trade_tags`` association table.

This module defines the many-to-many link between trades and tags.
No business logic lives here — it is a pure join table.
"""

import uuid

from sqlalchemy import ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TradeTag(Base):
    """Association table linking :class:`~app.models.trade.Trade` to
    :class:`~app.models.tag.Tag` in a many-to-many relationship.

    Attributes:
        trade_id: Foreign key to ``trades.id`` (composite primary key).
        tag_id: Foreign key to ``tags.id`` (composite primary key).
    """

    __tablename__ = "trade_tags"

    trade_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trades.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    )

    __table_args__ = (Index("ix_trade_tags_tag_id", "tag_id"),)

    def __repr__(self) -> str:
        """Return a human-readable string representation of the association.

        Returns:
            A debug string containing the trade_id and tag_id.
        """
        return f"<TradeTag trade_id={self.trade_id} tag_id={self.tag_id}>"
