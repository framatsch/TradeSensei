"""Business-logic service for authentication operations.

Handles user registration, login, token refresh, and logout.  All domain
exceptions raised here are caught by the route layer, which converts
them to HTTP responses.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
)
from app.core.security import (
    create_access_token,
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

    Owns the business rules for registration, login, token refresh, and
    logout.  Does **not** handle HTTP cookies or headers — that
    responsibility belongs to the route layer.

    Args:
        session: An open :class:`AsyncSession` managed by the caller.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with a database session.

        Args:
            session: The session to use for all operations.
        """
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
            raise UserAlreadyExistsError(
                f"Username {data.username!r} is already taken."
            )
        if await self._repo.get_by_email(data.email) is not None:
            raise UserAlreadyExistsError(f"Email {data.email!r} is already registered.")
        hashed = hash_password(data.password)
        return await self._repo.create(data, hashed)

    async def login(self, data: UserLogin) -> tuple[str, str]:
        """Authenticate a user and return a token pair.

        The ``username`` field accepts either a username or an email
        address.  The password is verified against the stored bcrypt hash.

        Args:
            data: Login credentials (username-or-email + password).

        Returns:
            A two-tuple of ``(access_token, refresh_token)`` strings.

        Raises:
            :class:`~app.core.exceptions.InvalidCredentialsError`: If
                no matching user exists or the password is incorrect, or
                the account is inactive.
        """
        # Support login by username OR email
        user = await self._repo.get_by_username(data.username)
        if user is None:
            user = await self._repo.get_by_email(data.username)
        if user is None or not verify_password(data.password, user.hashed_password):
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
                :meth:`login`.

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
