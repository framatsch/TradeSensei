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

"""SQLAlchemy ORM model for the ``used_otts`` table.

Stores consumed one-time token JTIs so that replays are rejected across
all processes.  The PRIMARY KEY on ``jti`` makes every insert atomic:
a duplicate raises ``IntegrityError``, which the caller treats as "already used".

Expired rows are pruned on every :func:`~app.core.security.consume_ott_jti`
call so the table stays small without a separate cron job.
"""

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UsedOtt(Base):
    """Row in the ``used_otts`` table representing a consumed one-time token JTI.

    Attributes:
        jti: The JWT ID claim of the consumed token (primary key).
        expires_at: When the original token would have expired (UTC).
            Used for bulk-pruning expired rows.
    """

    __tablename__ = "used_otts"

    jti: Mapped[str] = mapped_column(String, primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
