"""Async repository for the ``playbooks`` table.

All methods receive an :class:`AsyncSession` from the service layer and
return SQLAlchemy ORM instances.  No business logic lives here.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.playbook import Playbook
from app.schemas.playbook import PlaybookCreate, PlaybookUpdate


class PlaybookRepository:
    """Data-access object for the ``playbooks`` table.

    Every query is scoped to a ``user_id`` so that users can never see
    or modify each other's playbooks.

    Args:
        session: An open :class:`AsyncSession` managed by the caller.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the repository with an existing session.

        Args:
            session: The database session to use for all queries.
        """
        self._session = session

    async def get_by_id(
        self,
        playbook_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Playbook | None:
        """Retrieve a single playbook by primary key, scoped to a user.

        Args:
            playbook_id: UUID of the playbook to fetch.
            user_id: UUID of the requesting user — enforces isolation.

        Returns:
            The matching :class:`Playbook`, or ``None`` if not found or
            not owned by the given user.
        """
        result = await self._session.execute(
            select(Playbook).where(
                Playbook.id == playbook_id,
                Playbook.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_name(
        self,
        name: str,
        user_id: uuid.UUID,
    ) -> Playbook | None:
        """Retrieve a playbook by name, scoped to a user.

        Args:
            name: The playbook name to search for.
            user_id: UUID of the requesting user.

        Returns:
            The matching :class:`Playbook`, or ``None`` if not found.
        """
        result = await self._session.execute(
            select(Playbook).where(
                Playbook.name == name,
                Playbook.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: uuid.UUID) -> list[Playbook]:
        """Return all playbooks owned by the given user.

        Results are ordered by ``created_at`` ascending for stability.

        Args:
            user_id: UUID of the user whose playbooks to list.

        Returns:
            A list of :class:`Playbook` ORM instances (may be empty).
        """
        result = await self._session.execute(
            select(Playbook)
            .where(Playbook.user_id == user_id)
            .order_by(Playbook.created_at.asc())
        )
        return list(result.scalars().all())

    async def create(self, data: PlaybookCreate, user_id: uuid.UUID) -> Playbook:
        """Persist a new playbook and return the flushed ORM instance.

        The session is *flushed* so the database assigns server defaults
        but not committed — the service layer commits.

        Args:
            data: Validated playbook creation payload.
            user_id: UUID of the owning user.

        Returns:
            The newly created :class:`Playbook` with all server defaults
            populated.
        """
        playbook = Playbook(
            user_id=user_id,
            name=data.name,
            description=data.description,
        )
        self._session.add(playbook)
        await self._session.flush()
        await self._session.refresh(playbook)
        return playbook

    async def update(
        self,
        playbook: Playbook,
        data: PlaybookUpdate,
    ) -> Playbook:
        """Apply a partial update to an existing playbook.

        Only fields explicitly set in *data* (non-``None``) are written.
        The session is flushed but not committed.

        Args:
            playbook: The ORM instance to update.
            data: Validated partial update payload.

        Returns:
            The updated :class:`Playbook` instance after flush.
        """
        update_dict = data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(playbook, field, value)
        self._session.add(playbook)
        await self._session.flush()
        await self._session.refresh(playbook)
        return playbook

    async def delete(self, playbook: Playbook) -> None:
        """Delete a playbook from the database.

        The session is flushed but not committed.

        Args:
            playbook: The ORM instance to delete.
        """
        await self._session.delete(playbook)
        await self._session.flush()
