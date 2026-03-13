"""Async repository for the ``users`` table.

All methods receive an :class:`AsyncSession` from the service layer and
return SQLAlchemy ORM instances.  No business logic lives here.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserCreate


class UserRepository:
    """Data-access object for the ``users`` table.

    Accepts an :class:`AsyncSession` at construction time so that the
    same database transaction can span multiple repository calls.

    Args:
        session: An open :class:`AsyncSession` managed by the caller.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the repository with an existing session.

        Args:
            session: The database session to use for all queries.
        """
        self._session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Retrieve a single user by primary key.

        Args:
            user_id: UUID of the user to fetch.

        Returns:
            The matching :class:`User`, or ``None`` if not found.
        """
        result = await self._session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        """Retrieve a single user by their username.

        Args:
            username: The username to look up (case-sensitive).

        Returns:
            The matching :class:`User`, or ``None`` if not found.
        """
        result = await self._session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Retrieve a single user by their email address.

        Args:
            email: The email to look up (case-sensitive).

        Returns:
            The matching :class:`User`, or ``None`` if not found.
        """
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(self, data: UserCreate, hashed_password: str) -> User:
        """Persist a new user and return the flushed ORM instance.

        The session is *flushed* so the database assigns server defaults
        (e.g. ``id``, ``created_at``) but not committed — the service
        layer is responsible for committing.

        Args:
            data: Validated user creation payload (password field ignored).
            hashed_password: The bcrypt hash of the user's plain-text password.

        Returns:
            The newly created :class:`User` with all server defaults populated.
        """
        user = User(
            username=data.username,
            email=data.email,
            hashed_password=hashed_password,
        )
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def update(self, user: User, data: dict[str, object]) -> User:
        """Apply a partial update to an existing user.

        Only the keys present in *data* are written.  The session is
        flushed but not committed.

        Args:
            user: The ORM instance to update (already loaded from DB).
            data: Dictionary of field names to new values.

        Returns:
            The updated :class:`User` instance after flush.
        """
        for field, value in data.items():
            setattr(user, field, value)
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def delete(self, user: User) -> None:
        """Delete a user from the database.

        Cascades to all owned accounts (and, transitively, their trades).
        The session is flushed but not committed.

        Args:
            user: The ORM instance to delete.
        """
        await self._session.delete(user)
        await self._session.flush()

    async def increment_token_version(self, user: User) -> None:
        """Increment the refresh token version counter for a user.

        Incrementing this counter invalidates all previously issued refresh
        tokens for the user, effectively revoking all active sessions.
        The session is flushed but not committed.

        Args:
            user: The ORM instance whose version counter should be incremented.
        """
        user.refresh_token_version += 1
        self._session.add(user)
        await self._session.flush()
