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

"""Business-logic service for playbook operations.

This layer orchestrates the repository and owns transaction semantics.
No HTTP concepts (``Request``, ``Response``, status codes) appear here.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PlaybookNotFoundError
from app.repositories.playbook_repository import PlaybookRepository
from app.schemas.playbook import PlaybookCreate, PlaybookRead, PlaybookUpdate


class PlaybookService:
    """Service layer for playbook CRUD operations.

    All operations are scoped to a ``user_id`` so that users can only
    see and modify their own playbooks.

    Args:
        session: An open :class:`AsyncSession` managed by the caller.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with a database session.

        Args:
            session: The session to use for all operations within this
                request.
        """
        self._repo = PlaybookRepository(session)

    async def list_playbooks(self, user_id: uuid.UUID) -> list[PlaybookRead]:
        """Return all playbooks owned by the given user.

        Args:
            user_id: UUID of the authenticated user.

        Returns:
            A list of :class:`PlaybookRead` DTOs (may be empty).
        """
        playbooks = await self._repo.list_by_user(user_id)
        return [PlaybookRead.model_validate(p) for p in playbooks]

    async def get_playbook(
        self,
        playbook_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> PlaybookRead:
        """Retrieve a single playbook by ID, scoped to the requesting user.

        Args:
            playbook_id: UUID of the playbook to retrieve.
            user_id: UUID of the authenticated user.

        Returns:
            A :class:`PlaybookRead` DTO.

        Raises:
            PlaybookNotFoundError: If no playbook with that ID exists
                for the requesting user.
        """
        playbook = await self._repo.get_by_id(playbook_id, user_id)
        if playbook is None:
            raise PlaybookNotFoundError(f"Playbook {playbook_id} not found.")
        return PlaybookRead.model_validate(playbook)

    async def create_playbook(
        self,
        data: PlaybookCreate,
        user_id: uuid.UUID,
    ) -> PlaybookRead:
        """Create a new playbook for the given user.

        Args:
            data: Validated playbook creation payload.
            user_id: UUID of the authenticated user.

        Returns:
            A :class:`PlaybookRead` DTO for the newly created playbook.
        """
        playbook = await self._repo.create(data, user_id)
        return PlaybookRead.model_validate(playbook)

    async def update_playbook(
        self,
        playbook_id: uuid.UUID,
        data: PlaybookUpdate,
        user_id: uuid.UUID,
    ) -> PlaybookRead:
        """Apply a partial update to a playbook owned by the given user.

        Args:
            playbook_id: UUID of the playbook to update.
            data: Validated partial update payload.
            user_id: UUID of the authenticated user.

        Returns:
            A :class:`PlaybookRead` DTO reflecting the updated state.

        Raises:
            PlaybookNotFoundError: If no playbook with that ID exists
                for the requesting user.
        """
        playbook = await self._repo.get_by_id(playbook_id, user_id)
        if playbook is None:
            raise PlaybookNotFoundError(f"Playbook {playbook_id} not found.")
        updated = await self._repo.update(playbook, data)
        return PlaybookRead.model_validate(updated)

    async def delete_playbook(
        self,
        playbook_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Delete a playbook owned by the given user.

        Args:
            playbook_id: UUID of the playbook to delete.
            user_id: UUID of the authenticated user.

        Raises:
            PlaybookNotFoundError: If no playbook with that ID exists
                for the requesting user.
        """
        playbook = await self._repo.get_by_id(playbook_id, user_id)
        if playbook is None:
            raise PlaybookNotFoundError(f"Playbook {playbook_id} not found.")
        await self._repo.delete(playbook)
