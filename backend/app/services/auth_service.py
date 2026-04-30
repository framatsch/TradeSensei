"""Business-logic service for authentication operations.

Handles user registration, login, token refresh, logout, and Google OAuth.
All domain exceptions raised here are caught by the route layer, which
converts them to HTTP responses.
"""

import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
)
from app.core.security import (
    consume_one_time_token,
    create_access_token,
    create_one_time_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserLogin


class AuthService:
    """Service layer for authentication operations.

    Owns the business rules for registration, login, token refresh,
    logout, and Google OAuth.  Does **not** handle HTTP cookies or
    headers — that responsibility belongs to the route layer.

    Args:
        session: An open :class:`AsyncSession` managed by the caller.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with a database session.

        Args:
            session: The session to use for all operations.
        """
        self._session = session
        self._repo = UserRepository(session)

    async def register(self, data: UserCreate) -> User:
        """Register a new user account.

        Checks that neither the username nor the email is already taken,
        then persists the new user with a hashed password.

        Args:
            data: Validated registration payload.

        Returns:
            The newly created :class:`~app.models.user.User` ORM instance.

        Raises:
            :class:`~app.core.exceptions.UserAlreadyExistsError`: If the
                username or email is already registered.
        """
        if await self._repo.get_by_username(data.username) is not None:
            raise UserAlreadyExistsError(f"Username {data.username!r} is already taken.")
        if await self._repo.get_by_email(data.email) is not None:
            raise UserAlreadyExistsError(f"Email {data.email!r} is already registered.")
        hashed = hash_password(data.password)
        return await self._repo.create(data, hashed)

    async def login(self, data: UserLogin) -> tuple[str, str]:
        """Authenticate a user and return a token pair.

        The ``username`` field accepts either a username or an email
        address.  The password is verified against the stored bcrypt hash.
        OAuth-only accounts (``provider != 'local'``) cannot log in with
        a password and will receive an :class:`InvalidCredentialsError`.

        Args:
            data: Login credentials (username-or-email + password).

        Returns:
            A two-tuple of ``(access_token, refresh_token)`` strings.

        Raises:
            :class:`~app.core.exceptions.InvalidCredentialsError`: If
                no matching user exists, the password is incorrect, the
                account is inactive, or the account is OAuth-only.
        """
        # Support login by username OR email
        user = await self._repo.get_by_username(data.username)
        if user is None:
            user = await self._repo.get_by_email(data.username)
        if user is None:
            raise InvalidCredentialsError("Invalid username/email or password.")
        # OAuth-only users have no local password
        hashed = user.hashed_password
        if user.provider != "local" or hashed is None:
            raise InvalidCredentialsError("This account uses Google login. Please sign in with Google.")
        if not verify_password(data.password, hashed):
            raise InvalidCredentialsError("Invalid username/email or password.")
        if not user.is_active:
            raise InvalidCredentialsError("User account is disabled.")
        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id, user.refresh_token_version)
        return access_token, refresh_token

    async def refresh(self, refresh_token: str) -> tuple[str, str]:
        """Validate a refresh token and issue a new token pair.

        Validates the token signature, expiry, and version counter.  On
        success the token version is incremented (token rotation), which
        also invalidates the old refresh token.

        Args:
            refresh_token: A long-lived refresh JWT previously issued by
                :meth:`login` or :meth:`google_oauth_login`.

        Returns:
            A two-tuple of ``(new_access_token, new_refresh_token)`` strings.

        Raises:
            :class:`~app.core.exceptions.InvalidCredentialsError`: If the
                token is invalid, expired, the version has been revoked, or
                the user no longer exists or is inactive.
        """
        try:
            user_id, token_version = decode_refresh_token(refresh_token)
        except InvalidTokenError as exc:
            raise InvalidCredentialsError("Invalid or expired refresh token.") from exc
        user = await self._repo.get_by_id(user_id)
        if user is None or not user.is_active:
            raise InvalidCredentialsError("User not found or inactive.")
        if token_version != user.refresh_token_version:
            raise InvalidCredentialsError("Refresh token has been revoked.")
        # Rotate: increment version so the old token is invalidated
        await self._repo.increment_token_version(user)
        new_access_token = create_access_token(user.id)
        new_refresh_token = create_refresh_token(user.id, user.refresh_token_version)
        return new_access_token, new_refresh_token

    async def logout(self, user: User) -> None:
        """Invalidate all refresh tokens for the given user.

        Increments the user's ``refresh_token_version`` counter so that
        any previously issued refresh tokens are rejected on their next
        use.

        Args:
            user: The authenticated :class:`~app.models.user.User` to log out.
        """
        await self._repo.increment_token_version(user)

    async def external_oauth_login(
        self,
        provider: str,
        provider_sub: str,
        email: str,
        display_name: str,
        email_verified: bool,
    ) -> tuple[str, str, str]:
        """Authenticate or provision a user via an external OAuth provider.

        Lookup order:
        1. Existing user with matching ``provider_id`` (returning existing user).
        2. Existing local user with the same email (auto-link their account).
        3. No match → create a new OAuth-only user.

        Args:
            provider: Name of the OAuth provider (e.g., 'google', 'oidc').
            provider_sub: The provider's ``sub`` claim (stable user identifier).
            email: The user's verified email from the provider.
            display_name: Display name, used to derive a username.
            email_verified: Whether the provider has verified the email address.

        Returns:
            A three-tuple of
            ``(access_token, refresh_token, one_time_token)`` strings.

        Raises:
            :class:`~app.core.exceptions.InvalidCredentialsError`: If the
                email is not verified or the user account is inactive.
        """
        if not email_verified:
            raise InvalidCredentialsError(f"{provider} account email is not verified.")

        # 1. Existing OAuth user
        user = await self._repo.get_by_provider_id(provider, provider_sub)

        if user is None:
            # 2. Existing local user with same email → auto-link
            existing = await self._repo.get_by_email(email)
            if existing is not None:
                user = await self._repo.link_oauth_account(existing, provider, provider_sub)
            else:
                # 3. Create new OAuth user
                username = await self._derive_unique_username(display_name)
                user = await self._repo.create_oauth_user(
                    email=email,
                    username=username,
                    provider=provider,
                    provider_id=provider_sub,
                )

        if not user.is_active:
            raise InvalidCredentialsError("User account is disabled.")

        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id, user.refresh_token_version)
        one_time_token = create_one_time_token(user.id)
        return access_token, refresh_token, one_time_token

    async def exchange_one_time_token(self, ott: str) -> tuple[str, str]:
        """Exchange a one-time OAuth token for a full access + refresh pair.

        The one-time token is consumed (invalidated) on first use.

        Args:
            ott: The short-lived one-time JWT from the OAuth callback redirect.

        Returns:
            A two-tuple of ``(access_token, refresh_token)`` strings.

        Raises:
            :class:`~app.core.exceptions.InvalidCredentialsError`: If the
                token is invalid, expired, or already used.
        """
        try:
            user_id = await consume_one_time_token(ott, self._session)
        except InvalidTokenError as exc:
            raise InvalidCredentialsError("Invalid or expired one-time token.") from exc
        user = await self._repo.get_by_id(user_id)
        if user is None or not user.is_active:
            raise InvalidCredentialsError("User not found or inactive.")
        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id, user.refresh_token_version)
        return access_token, refresh_token

    async def get_user_by_email(self, email: str) -> User | None:
        """Return the user with the given email address, or None.

        Args:
            email: Email address to look up.

        Returns:
            The matching :class:`~app.models.user.User`, or ``None``.
        """
        return await self._repo.get_by_email(email)

    async def update_password(self, user_id: "uuid.UUID", hashed: str) -> None:
        """Replace the stored password hash and invalidate all active sessions.

        Increments ``refresh_token_version`` so every previously issued
        refresh token is immediately rejected.

        Args:
            user_id: UUID of the user whose password should be updated.
            hashed: New bcrypt hash to persist.
        """
        user = await self._repo.get_by_id(user_id)
        if user is None:
            return
        user.hashed_password = hashed
        user.refresh_token_version += 1

    async def _derive_unique_username(self, display_name: str) -> str:
        """Derive a unique username from a Google display name.

        Strips non-alphanumeric characters, lowercases, trims to 40 chars,
        and appends a numeric suffix if the base name is taken.

        Args:
            display_name: Raw display name from Google.

        Returns:
            A unique username string safe for storage.
        """
        base = re.sub(r"[^a-z0-9]", "", display_name.lower())[:40] or "user"
        candidate = base
        counter = 2
        while await self._repo.get_by_username(candidate) is not None:
            candidate = f"{base}{counter}"
            counter += 1
        return candidate
