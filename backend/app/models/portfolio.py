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
    from app.models.saved_dashboard_view import SavedDashboardView
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
        cascade="all, delete-orphan",
    )
    saved_dashboard_views: Mapped[list["SavedDashboardView"]] = relationship(
        "SavedDashboardView",
        back_populates="portfolio",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_portfolios_user_name"),
        CheckConstraint(
            "color_hex IS NULL OR color_hex ~ '^#[0-9A-Fa-f]{6}$'",
            name="ck_portfolios_color_hex",
        ),
        Index("ix_portfolios_user_id", "user_id"),
    )
