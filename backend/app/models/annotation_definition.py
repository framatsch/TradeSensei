# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""SQLAlchemy ORM model for reusable annotation definitions."""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.checkin_annotation import CheckinAnnotation
    from app.models.trade_annotation import TradeAnnotation
    from app.models.user import User


class AnnotationType(StrEnum):
    """Allowed annotation value types."""

    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    STRING_ENUM = "string_enum"


class AnnotationDefinition(Base):
    """Reusable annotation definition assignable to trades and/or check-ins."""

    __tablename__ = "annotation_definitions"

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
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    scope: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    scale_labels: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
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

    trade_assignments: Mapped[list["TradeAnnotation"]] = relationship(
        "TradeAnnotation",
        back_populates="annotation_definition",
        passive_deletes=True,
    )
    checkin_assignments: Mapped[list["CheckinAnnotation"]] = relationship(
        "CheckinAnnotation",
        back_populates="annotation_definition",
        passive_deletes=True,
    )
    user: Mapped["User"] = relationship("User")

    __table_args__ = (
        UniqueConstraint("user_id", "name", "scope", name="uq_annotation_definitions_user_name_scope"),
        Index("ix_annotation_definitions_user_id", "user_id"),
        Index("ix_annotation_definitions_scope", "scope"),
        Index("ix_annotation_definitions_archived", "is_archived"),
    )
