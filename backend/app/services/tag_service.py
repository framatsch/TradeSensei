"""Business-logic service for tag operations.

This layer orchestrates the repository and owns transaction semantics.
No HTTP concepts (``Request``, ``Response``, status codes) appear here.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import TagNotFoundError
from app.repositories.tag_repository import TagRepository
from app.schemas.tag import TagCreate, TagRead, TagUpdate


class TagService:
    """Service layer for tag CRUD operations.

    All operations are scoped to a ``user_id`` so that users can only
    see and modify their own tags.

    Args:
        session: An open :class:`AsyncSession` managed by the caller.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with a database session.

        Args:
            session: The session to use for all operations within this
                request.
        """
        self._repo = TagRepository(session)

    async def list_tags(self, user_id: uuid.UUID) -> list[TagRead]:
        """Return all tags owned by the given user.

        Args:
            user_id: UUID of the authenticated user.

        Returns:
            A list of :class:`TagRead` DTOs (may be empty).
        """
        tags = await self._repo.list_by_user(user_id)
        return [TagRead.model_validate(t) for t in tags]

    async def get_tag(
        self,
        tag_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> TagRead:
        """Retrieve a single tag by ID, scoped to the requesting user.

        Args:
            tag_id: UUID of the tag to retrieve.
            user_id: UUID of the authenticated user.

        Returns:
            A :class:`TagRead` DTO.

        Raises:
            TagNotFoundError: If no tag with that ID exists for the
                requesting user.
        """
        tag = await self._repo.get_by_id(tag_id, user_id)
        if tag is None:
            raise TagNotFoundError(f"Tag {tag_id} not found.")
        return TagRead.model_validate(tag)

    async def create_tag(
        self,
        data: TagCreate,
        user_id: uuid.UUID,
    ) -> TagRead:
        """Create a new tag for the given user.

        Args:
            data: Validated tag creation payload.
            user_id: UUID of the authenticated user.

        Returns:
            A :class:`TagRead` DTO for the newly created tag.
        """
        tag = await self._repo.create(data, user_id)
        return TagRead.model_validate(tag)

    async def update_tag(
        self,
        tag_id: uuid.UUID,
        data: TagUpdate,
        user_id: uuid.UUID,
    ) -> TagRead:
        """Apply a partial update to a tag owned by the given user.

        Args:
            tag_id: UUID of the tag to update.
            data: Validated partial update payload.
            user_id: UUID of the authenticated user.

        Returns:
            A :class:`TagRead` DTO reflecting the updated state.

        Raises:
            TagNotFoundError: If no tag with that ID exists for the
                requesting user.
        """
        tag = await self._repo.get_by_id(tag_id, user_id)
        if tag is None:
            raise TagNotFoundError(f"Tag {tag_id} not found.")
        updated = await self._repo.update(tag, data)
        return TagRead.model_validate(updated)

    async def delete_tag(
        self,
        tag_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Delete a tag owned by the given user.

        Args:
            tag_id: UUID of the tag to delete.
            user_id: UUID of the authenticated user.

        Raises:
            TagNotFoundError: If no tag with that ID exists for the
                requesting user.
        """
        tag = await self._repo.get_by_id(tag_id, user_id)
        if tag is None:
            raise TagNotFoundError(f"Tag {tag_id} not found.")
        await self._repo.delete(tag)
