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

"""Business-logic service for corporate action operations.

This layer orchestrates the repository and owns transaction semantics.
No HTTP concepts (``Request``, ``Response``, status codes) appear here.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CorporateActionNotFoundError
from app.models.corporate_action import CorporateAction
from app.repositories.corporate_action_repository import CorporateActionRepository
from app.schemas.corporate_action import (
    CorporateActionCreate,
    CorporateActionRead,
    CorporateActionUpdate,
)


class CorporateActionService:
    """Service layer for corporate action CRUD operations.

    All operations are scoped to a ``user_id`` so that users can only
    see and modify their own corporate actions.

    Args:
        session: An open :class:`AsyncSession` managed by the caller.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with a database session.

        Args:
            session: The session to use for all operations within this request.
        """
        self._repo = CorporateActionRepository(session)
        self._session = session

    async def list_corporate_actions(self, user_id: uuid.UUID) -> list[CorporateActionRead]:
        """Return all corporate actions owned by the given user.

        Args:
            user_id: UUID of the authenticated user.

        Returns:
            A list of :class:`CorporateActionRead` DTOs ordered by date ascending
            (may be empty).
        """
        actions = await self._repo.list_by_user(user_id)
        return [CorporateActionRead.model_validate(a) for a in actions]

    async def list_for_aggregator(self, user_id: uuid.UUID) -> list[CorporateAction]:
        """Return raw ORM objects for use by the FIFO aggregator.

        Unlike :meth:`list_corporate_actions` this method returns ORM instances
        rather than DTOs so the aggregator can access all fields directly.

        Args:
            user_id: UUID of the authenticated user.

        Returns:
            A list of :class:`~app.models.corporate_action.CorporateAction`
            instances ordered ascending by date.
        """
        return await self._repo.list_by_user(user_id)

    async def list_for_execution(
        self,
        user_id: uuid.UUID,
        *,
        symbol: str,
        conid: str | None,
    ) -> list[CorporateAction]:
        """Return corporate actions scoped for one execution leg.

        This narrows the candidate action set for trade-detail read paths.
        """
        return await self._repo.list_by_user_and_symbol_or_conid(
            user_id,
            symbol,
            conid,
        )

    async def get_corporate_action(
        self,
        action_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> CorporateActionRead:
        """Retrieve a single corporate action by ID, scoped to the requesting user.

        Args:
            action_id: UUID of the corporate action to retrieve.
            user_id: UUID of the authenticated user.

        Returns:
            A :class:`CorporateActionRead` DTO.

        Raises:
            CorporateActionNotFoundError: If no corporate action with that ID
                exists for the requesting user.
        """
        action = await self._repo.get_by_id(action_id, user_id)
        if action is None:
            raise CorporateActionNotFoundError(f"Corporate action {action_id} not found.")
        return CorporateActionRead.model_validate(action)

    async def create_corporate_action(
        self,
        data: CorporateActionCreate,
        user_id: uuid.UUID,
    ) -> CorporateActionRead:
        """Create a new corporate action for the given user.

        Args:
            data: Validated corporate action creation payload.
            user_id: UUID of the authenticated user.

        Returns:
            A :class:`CorporateActionRead` DTO for the newly created record.
        """
        data.user_id = user_id
        action = await self._repo.create(data)
        await self._session.commit()
        await self._session.refresh(action)
        return CorporateActionRead.model_validate(action)

    async def update_corporate_action(
        self,
        action_id: uuid.UUID,
        data: CorporateActionUpdate,
        user_id: uuid.UUID,
    ) -> CorporateActionRead:
        """Update an existing corporate action.

        Ownership is verified before applying any changes — a user cannot
        update another user's records.

        Args:
            action_id: UUID of the corporate action to update.
            data: Validated partial update payload.
            user_id: UUID of the authenticated user.

        Returns:
            A :class:`CorporateActionRead` DTO for the updated record.

        Raises:
            CorporateActionNotFoundError: If the record does not exist or is
                not owned by the requesting user.
        """
        action = await self._repo.get_by_id(action_id, user_id)
        if action is None:
            raise CorporateActionNotFoundError(f"Corporate action {action_id} not found.")
        action = await self._repo.update(action, data)
        await self._session.commit()
        await self._session.refresh(action)
        return CorporateActionRead.model_validate(action)

    async def delete_corporate_action(
        self,
        action_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Delete a corporate action record.

        Ownership is verified before deletion — a user cannot delete another
        user's records.

        Args:
            action_id: UUID of the corporate action to delete.
            user_id: UUID of the authenticated user.

        Raises:
            CorporateActionNotFoundError: If the record does not exist or is
                not owned by the requesting user.
        """
        action = await self._repo.get_by_id(action_id, user_id)
        if action is None:
            raise CorporateActionNotFoundError(f"Corporate action {action_id} not found.")
        await self._repo.delete(action)
        await self._session.commit()
