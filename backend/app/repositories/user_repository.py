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
        result = await self._session.execute(select(User).where(User.username == username))
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

    async def get_by_provider_id(self, provider: str, provider_id: str) -> User | None:
        """Retrieve a single user by their OAuth provider and provider ID.

        Args:
            provider: The authentication provider (e.g. ``'google'``).
            provider_id: The provider-specific user identifier (e.g. Google
                ``sub`` claim).

        Returns:
            The matching :class:`User`, or ``None`` if not found.
        """
        result = await self._session.execute(
            select(User).where(
                User.provider == provider,
                User.provider_id == provider_id,
            )
        )
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

    async def create_oauth_user(
        self,
        email: str,
        username: str,
        provider: str,
        provider_id: str,
    ) -> User:
        """Persist a new OAuth user without a local password.

        The session is *flushed* so the database assigns server defaults
        but not committed — the service layer is responsible for committing.

        Args:
            email: The user's email address from the OAuth provider.
            username: A unique username derived from the provider profile.
            provider: The authentication provider (e.g. ``'google'``).
            provider_id: The provider-specific user identifier.

        Returns:
            The newly created :class:`User` with all server defaults populated.
        """
        user = User(
            username=username,
            email=email,
            hashed_password=None,
            provider=provider,
            provider_id=provider_id,
        )
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def link_oauth_account(
        self,
        user: User,
        provider: str,
        provider_id: str,
    ) -> User:
        """Link an existing user to an OAuth provider.

        Updates the user's ``provider`` and ``provider_id`` to associate
        their account with the given OAuth provider.  The session is flushed
        but not committed.

        Args:
            user: The existing :class:`User` ORM instance to update.
            provider: The authentication provider (e.g. ``'google'``).
            provider_id: The provider-specific user identifier.

        Returns:
            The updated :class:`User` instance after flush.
        """
        user.provider = provider
        user.provider_id = provider_id
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
