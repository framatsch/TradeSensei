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

import uuid
from collections.abc import Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.saved_checkin_filter import SavedCheckinFilter


class SavedCheckinFilterRepository:
    """Repository for managing saved checkin filters in the database."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository for SavedCheckinFilter model."""
        self.session = session

    async def list_by_user(
        self,
        user_id: uuid.UUID,
    ) -> Sequence[SavedCheckinFilter]:
        """List all saved checkin filters for a specific user.

        Args:
            user_id: The ID of the user.

        Returns:
            A list of SavedCheckinFilter instances ordered by creation date.
        """
        stmt = (
            select(SavedCheckinFilter)
            .where(SavedCheckinFilter.user_id == user_id)
            .order_by(SavedCheckinFilter.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def unset_default(
        self,
        user_id: uuid.UUID,
        exclude_id: uuid.UUID | None = None,
    ) -> None:
        """Set is_default to False for all of a user's filters.

        Args:
            user_id: The ID of the user.
            exclude_id: Optional ID to exclude from the update.
        """
        stmt = (
            update(SavedCheckinFilter)
            .where(SavedCheckinFilter.user_id == user_id)
            .where(SavedCheckinFilter.is_default.is_(True))
        )
        if exclude_id:
            stmt = stmt.where(SavedCheckinFilter.id != exclude_id)
            
    async def create(
        self,
        **kwargs: object,
    ) -> SavedCheckinFilter:
        """Create a new saved checkin filter."""
        obj = SavedCheckinFilter(**kwargs)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def get_by_id(
        self,
        filter_id: uuid.UUID,
    ) -> SavedCheckinFilter | None:
        """Get a saved checkin filter by ID."""
        return await self.session.get(SavedCheckinFilter, filter_id)

    async def update(
        self,
        filter_id: uuid.UUID,
        **kwargs: object,
    ) -> SavedCheckinFilter | None:
        """Update a saved checkin filter."""
        obj = await self.get_by_id(filter_id)
        if not obj:
            return None
        for key, value in kwargs.items():
            setattr(obj, key, value)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def delete(
        self,
        filter_id: uuid.UUID,
    ) -> bool:
        """Delete a saved checkin filter."""
        obj = await self.get_by_id(filter_id)
        if not obj:
            return False
        await self.session.delete(obj)
        await self.session.flush()
        return True
