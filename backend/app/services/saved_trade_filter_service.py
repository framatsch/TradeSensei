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

"""Service layer for managing saved trade-filter presets."""

import uuid
from collections.abc import Sequence
from typing import Any

from app.core.exceptions import (
    SavedTradeFilterNotFoundError,
    SavedTradeFilterPermissionError,
    SavedTradeFilterValidationError,
)
from app.models.saved_trade_filter import FilterScope, SavedTradeFilter
from app.repositories.saved_trade_filter_repository import SavedTradeFilterRepository
from app.schemas.trade import TradeFilterParams


class SavedTradeFilterService:
    """Service for managing saved trade filters."""

    def __init__(self, repository: SavedTradeFilterRepository) -> None:
        """Initialize the service with a repository."""
        self.repository = repository

    def _validate_definition(self, definition: dict[str, Any]) -> None:
        """Validate that a definition only contains valid TradeFilterParams fields.

        Args:
            definition: The filter definition to validate.

        Raises:
            SavedTradeFilterValidationError: If the definition is invalid.
        """
        try:
            # Pydantic will validate the schema and strip unknowns or raise errors
            TradeFilterParams.model_validate(definition)
        except Exception as e:
            raise SavedTradeFilterValidationError(f"Invalid filter definition: {str(e)}") from e

    async def list_for_user(self, user_id: uuid.UUID) -> Sequence[SavedTradeFilter]:
        """List all saved filters visible to the user (system + their own)."""
        return await self.repository.list_for_user(user_id)

    async def create_user_filter(
        self,
        user_id: uuid.UUID,
        name: str,
        definition: dict[str, Any],
    ) -> SavedTradeFilter:
        """Create a new user-owned saved filter."""
        self._validate_definition(definition)

        return await self.repository.create(
            name=name,
            definition=definition,
            scope=FilterScope.USER,
            owner_id=user_id,
            needs_review=False,
        )

    async def update_user_filter(
        self,
        user_id: uuid.UUID,
        filter_id: uuid.UUID,
        name: str | None = None,
        definition: dict[str, Any] | None = None,
    ) -> SavedTradeFilter:
        """Update an existing user-owned saved filter."""
        db_filter = await self.repository.get_by_id(filter_id)
        if not db_filter:
            raise SavedTradeFilterNotFoundError("Saved trade filter not found")

        if db_filter.scope == FilterScope.SYSTEM:
            raise SavedTradeFilterPermissionError("Cannot modify system filters")

        if db_filter.owner_id != user_id:
            raise SavedTradeFilterPermissionError("Not authorized to modify this filter")

        if definition is not None:
            self._validate_definition(definition)

        # Clear needs_review flag on successful manual update
        needs_review = False if definition is not None else None

        return await self.repository.update(
            db_filter=db_filter,
            name=name,
            definition=definition,
            needs_review=needs_review,
        )

    async def delete_user_filter(
        self,
        user_id: uuid.UUID,
        filter_id: uuid.UUID,
    ) -> None:
        """Delete an existing user-owned saved filter."""
        db_filter = await self.repository.get_by_id(filter_id)
        if not db_filter:
            raise SavedTradeFilterNotFoundError("Saved trade filter not found")

        if db_filter.scope == FilterScope.SYSTEM:
            raise SavedTradeFilterPermissionError("Cannot modify system filters")

        if db_filter.owner_id != user_id:
            raise SavedTradeFilterPermissionError("Not authorized to modify this filter")

        await self.repository.delete(filter_id)
