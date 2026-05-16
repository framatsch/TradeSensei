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

"""Association model between check-ins and annotation definitions with typed values."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import NUMERIC_PRECISION, NUMERIC_SCALE
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.annotation_definition import AnnotationDefinition
    from app.models.daily_checkin import DailyCheckin


class CheckinAnnotation(Base):
    """Assignment table between a check-in and an annotation definition."""

    __tablename__ = "checkin_annotations"

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
    annotation_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("annotation_definitions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    value_int: Mapped[int | None] = mapped_column(nullable=True)
    value_float: Mapped[Decimal | None] = mapped_column(
        Numeric(NUMERIC_PRECISION, NUMERIC_SCALE),
        nullable=True,
    )
    value_bool: Mapped[bool | None] = mapped_column(nullable=True)
    value_string: Mapped[str | None] = mapped_column(String(255), nullable=True)
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

    checkin: Mapped["DailyCheckin"] = relationship(
        "DailyCheckin",
        back_populates="annotation_assignments",
    )
    annotation_definition: Mapped["AnnotationDefinition"] = relationship(
        "AnnotationDefinition",
        back_populates="checkin_assignments",
    )

    __table_args__ = (
        UniqueConstraint(
            "checkin_id",
            "annotation_definition_id",
            name="uq_checkin_annotation_pair",
        ),
        CheckConstraint(
            "num_nonnulls(value_int, value_float, value_bool, value_string) = 1",
            name="ck_checkin_annotations_exactly_one_value",
        ),
    )
