"""Business-logic service for user profile operations.

Provides read, update, and delete operations scoped to the currently
authenticated user.  All domain exceptions raised here are caught by
the route layer.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UserAlreadyExistsError, UserNotFoundError
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserRead, UserUpdate


class UserService:
    """Service layer for user profile management.

    All operations are implicitly scoped to the requesting user so that
    no user can read or modify another user's profile.

    Args:
        session: An open :class:`AsyncSession` managed by the caller.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with a database session.

        Args:
            session: The session to use for all operations.
        """
        self._repo = UserRepository(session)

    async def get_user(self, user_id: uuid.UUID) -> UserRead:
        """Return the profile DTO for the given user.

        Args:
            user_id: UUID of the user to retrieve.

        Returns:
            A :class:`~app.schemas.user.UserRead` DTO for the user.

        Raises:
            :class:`~app.core.exceptions.UserNotFoundError`: If the user
                no longer exists (should be rare in normal operation).
        """
        user = await self._repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(f"User {user_id} not found.")
        return UserRead.model_validate(user)

    async def update_user(self, user: User, data: UserUpdate) -> UserRead:
        """Apply a partial update to the given user's profile.

        Checks that any new username or email is not already taken by a
        different user before writing.

        Args:
            user: The ORM instance of the authenticated user.
            data: Validated partial update payload.

        Returns:
            A :class:`~app.schemas.user.UserRead` DTO reflecting the
            updated state.

        Raises:
            :class:`~app.core.exceptions.UserAlreadyExistsError`: If the
                requested username or email is already in use by another user.
        """
        update_dict = data.model_dump(exclude_unset=True)

        # Enforce uniqueness before writing
        new_username: str | None = update_dict.get("username")
        if new_username is not None and new_username != user.username:
            existing = await self._repo.get_by_username(new_username)
            if existing is not None:
                raise UserAlreadyExistsError(
                    f"Username {new_username!r} is already taken."
                )

        new_email: str | None = update_dict.get("email")
        if new_email is not None and new_email != user.email:
            existing = await self._repo.get_by_email(new_email)
            if existing is not None:
                raise UserAlreadyExistsError(
                    f"Email {new_email!r} is already registered."
                )

        # Strip None values — only write explicitly-provided non-null fields
        clean_dict: dict[str, object] = {
            k: v for k, v in update_dict.items() if v is not None
        }
        updated = await self._repo.update(user, clean_dict)
        return UserRead.model_validate(updated)

    async def delete_user(self, user: User) -> None:
        """Permanently delete the given user and all owned data.

        Args:
            user: The ORM instance of the authenticated user to delete.
        """
        await self._repo.delete(user)
