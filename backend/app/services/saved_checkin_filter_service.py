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

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.models.saved_checkin_filter import SavedCheckinFilter
from app.repositories.saved_checkin_filter_repository import SavedCheckinFilterRepository
from app.schemas.saved_checkin_filter import (
    SavedCheckinFilterCreate,
    SavedCheckinFilterUpdate,
)


class SavedCheckinFilterService:
    """Service layer for managing saved checkin filters."""

    def __init__(self, repo: SavedCheckinFilterRepository) -> None:
        """Initialize with repository."""
        self._repo = repo

    async def create(
        self,
        user_id: uuid.UUID,
        schema: SavedCheckinFilterCreate,
    ) -> SavedCheckinFilter:
        """Create a new saved checkin filter."""
        # Unset is_default on other filters if this one is set to default
        if schema.is_default:
            await self._repo.unset_default(user_id=user_id)

        try:
            return await self._repo.create(
                user_id=user_id,
                **schema.model_dump(),
            )
        except IntegrityError as exc:
            # Handle potential unique constraint violations (if any are added later)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Could not create saved filter due to a conflict.",
            ) from exc

    async def list_by_user(
        self,
        user_id: uuid.UUID,
    ) -> list[SavedCheckinFilter]:
        """List all saved checkin filters for a user."""
        return list(await self._repo.list_by_user(user_id=user_id))

    async def update(
        self,
        user_id: uuid.UUID,
        filter_id: uuid.UUID,
        schema: SavedCheckinFilterUpdate,
    ) -> SavedCheckinFilter:
        """Update an existing saved checkin filter."""
        # Get existing to ensure it belongs to user
        existing = await self._repo.get_by_id(filter_id)
        if not existing or existing.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Saved checkin filter not found.",
            )

        update_data = schema.model_dump(exclude_unset=True)
        if not update_data:
            return existing

        if update_data.get("is_default", False):
            await self._repo.unset_default(user_id=user_id, exclude_id=filter_id)

        try:
            updated = await self._repo.update(filter_id, **update_data)
            if not updated:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Saved checkin filter not found.",
                )
            return updated
        except IntegrityError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Could not update saved filter due to a conflict.",
            ) from exc

    async def delete(
        self,
        user_id: uuid.UUID,
        filter_id: uuid.UUID,
    ) -> None:
        """Delete a saved checkin filter."""
        # Check ownership
        existing = await self._repo.get_by_id(filter_id)
        if not existing or existing.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Saved checkin filter not found.",
            )

        deleted = await self._repo.delete(filter_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Saved checkin filter not found.",
            )
