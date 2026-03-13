"""Async repository for the ``tags`` table.

All methods receive an :class:`AsyncSession` from the service layer and
return SQLAlchemy ORM instances.  No business logic lives here.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tag import Tag
from app.schemas.tag import TagCreate, TagUpdate


class TagRepository:
    """Data-access object for the ``tags`` table.

    Every query is scoped to a ``user_id`` so that users can never see
    or modify each other's tags.

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
        tag_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Tag | None:
        """Retrieve a single tag by primary key, scoped to a user.

        Args:
            tag_id: UUID of the tag to fetch.
            user_id: UUID of the requesting user — enforces isolation.

        Returns:
            The matching :class:`Tag`, or ``None`` if not found or
            not owned by the given user.
        """
        result = await self._session.execute(
            select(Tag).where(
                Tag.id == tag_id,
                Tag.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_many_by_ids(
        self,
        tag_ids: list[uuid.UUID],
        user_id: uuid.UUID,
    ) -> list[Tag]:
        """Retrieve multiple tags by primary keys, scoped to a user.

        Only tags that exist and belong to the given user are returned;
        missing IDs are silently omitted.

        Args:
            tag_ids: List of tag UUIDs to fetch.
            user_id: UUID of the requesting user.

        Returns:
            A list of :class:`Tag` instances (length <= len(tag_ids)).
        """
        if not tag_ids:
            return []
        result = await self._session.execute(
            select(Tag).where(
                Tag.id.in_(tag_ids),
                Tag.user_id == user_id,
            )
        )
        return list(result.scalars().all())

    async def list_by_user(self, user_id: uuid.UUID) -> list[Tag]:
        """Return all tags owned by the given user.

        Results are ordered by ``name`` ascending for stability.

        Args:
            user_id: UUID of the user whose tags to list.

        Returns:
            A list of :class:`Tag` ORM instances (may be empty).
        """
        result = await self._session.execute(
            select(Tag).where(Tag.user_id == user_id).order_by(Tag.name.asc())
        )
        return list(result.scalars().all())

    async def create(self, data: TagCreate, user_id: uuid.UUID) -> Tag:
        """Persist a new tag and return the flushed ORM instance.

        The session is *flushed* so the database assigns server defaults
        but not committed — the service layer commits.

        Args:
            data: Validated tag creation payload.
            user_id: UUID of the owning user.

        Returns:
            The newly created :class:`Tag` with all server defaults
            populated.
        """
        tag = Tag(
            user_id=user_id,
            name=data.name,
            color=data.color,
        )
        self._session.add(tag)
        await self._session.flush()
        await self._session.refresh(tag)
        return tag

    async def update(
        self,
        tag: Tag,
        data: TagUpdate,
    ) -> Tag:
        """Apply a partial update to an existing tag.

        Only fields explicitly set in *data* (non-``None``) are written.
        The session is flushed but not committed.

        Args:
            tag: The ORM instance to update.
            data: Validated partial update payload.

        Returns:
            The updated :class:`Tag` instance after flush.
        """
        update_dict = data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(tag, field, value)
        self._session.add(tag)
        await self._session.flush()
        await self._session.refresh(tag)
        return tag

    async def delete(self, tag: Tag) -> None:
        """Delete a tag from the database.

        The session is flushed but not committed.

        Args:
            tag: The ORM instance to delete.
        """
        await self._session.delete(tag)
        await self._session.flush()
