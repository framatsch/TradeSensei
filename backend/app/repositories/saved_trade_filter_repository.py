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
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.saved_trade_filter import FilterScope, SavedTradeFilter


class SavedTradeFilterRepository:
    """Repository for managing saved trade filters."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with a database session."""
        self.session = session

    async def create(
        self,
        name: str,
        definition: dict[str, Any],
        scope: FilterScope,
        owner_id: uuid.UUID | None = None,
        needs_review: bool = False,
    ) -> SavedTradeFilter:
        """Create a new saved trade filter."""
        db_filter = SavedTradeFilter(
            name=name,
            definition=definition,
            scope=scope,
            owner_id=owner_id,
            needs_review=needs_review,
        )
        self.session.add(db_filter)
        await self.session.flush()
        await self.session.refresh(db_filter)
        return db_filter

    async def get_by_id(self, filter_id: uuid.UUID) -> SavedTradeFilter | None:
        """Get a saved filter by ID."""
        result = await self.session.execute(select(SavedTradeFilter).where(SavedTradeFilter.id == filter_id))
        return result.scalar_one_or_none()

    async def get_by_id_and_owner(self, filter_id: uuid.UUID, owner_id: uuid.UUID) -> SavedTradeFilter | None:
        """Get a saved filter by ID, ensuring it belongs to the user."""
        result = await self.session.execute(
            select(SavedTradeFilter).where(
                SavedTradeFilter.id == filter_id,
                SavedTradeFilter.owner_id == owner_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: uuid.UUID) -> Sequence[SavedTradeFilter]:
        """List all saved filters visible to a user (system + user's own)."""
        result = await self.session.execute(
            select(SavedTradeFilter)
            .where((SavedTradeFilter.scope == FilterScope.SYSTEM) | (SavedTradeFilter.owner_id == user_id))
            .order_by(SavedTradeFilter.scope, SavedTradeFilter.name)
        )
        return result.scalars().all()

    async def update(
        self,
        db_filter: SavedTradeFilter,
        name: str | None = None,
        definition: dict[str, Any] | None = None,
        needs_review: bool | None = None,
    ) -> SavedTradeFilter:
        """Update an existing saved filter."""
        if name is not None:
            db_filter.name = name
        if definition is not None:
            db_filter.definition = definition
        if needs_review is not None:
            db_filter.needs_review = needs_review

        await self.session.flush()
        await self.session.refresh(db_filter)
        return db_filter

    async def delete(self, filter_id: uuid.UUID) -> None:
        """Delete a saved filter."""
        await self.session.execute(delete(SavedTradeFilter).where(SavedTradeFilter.id == filter_id))
        await self.session.flush()
