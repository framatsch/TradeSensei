"""Association model between playbooks and taxonomy definitions."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.playbook import Playbook
    from app.models.taxonomy import Taxonomy


class PlaybookTaxonomy(Base):
    """Assignment table between a playbook and a taxonomy definition."""

    __tablename__ = "playbook_taxonomies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    playbook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("playbooks.id", ondelete="CASCADE"),
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

    playbook: Mapped["Playbook"] = relationship(
        "Playbook",
        back_populates="taxonomy_assignments",
    )
    taxonomy: Mapped["Taxonomy"] = relationship(
        "Taxonomy",
        back_populates="playbook_assignments",
    )

    __table_args__ = (UniqueConstraint("playbook_id", "taxonomy_id", name="uq_playbook_taxonomy_pair"),)
