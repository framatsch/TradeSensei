"""FastAPI dependencies for authentication and session management.

The :func:`get_current_user` dependency validates the Bearer token and
returns the active :class:`~app.models.user.User` ORM instance, raising
HTTP 401 when the token is invalid or the user is inactive.

The :func:`get_session_with_rls` dependency builds on top of
:func:`get_current_user` to set ``app.current_user_id`` via
``SET LOCAL`` so PostgreSQL Row-Level Security policies can filter rows
automatically for the authenticated user.
"""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.exceptions import InvalidTokenError
from app.core.security import decode_token
from app.models.user import User
from app.repositories.user_repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")
"""OAuth2 bearer scheme pointing at the token endpoint."""


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    """Decode the Bearer JWT and return the authenticated user.

    This dependency is injected into any route that requires authentication.
    It decodes the token, looks up the user in the database, and raises
    HTTP 401 if the token is invalid, expired, or the user is inactive.

    Args:
        token: The raw Bearer token string extracted from the Authorization header.
        session: The active database session.

    Returns:
        The authenticated :class:`~app.models.user.User` ORM instance.

    Raises:
        :class:`fastapi.HTTPException`: 401 if the token is invalid or
            the associated user does not exist or is inactive.
    """
    try:
        user_id = decode_token(token)
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_session_with_rls(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AsyncGenerator[AsyncSession]:
    """Yield a session with PostgreSQL RLS context set for the current user.

    Executes ``SET LOCAL app.current_user_id = :uid`` within the current
    transaction so that all RLS policies keyed on
    ``current_setting('app.current_user_id', true)::uuid`` automatically
    filter rows to the authenticated user only.

    ``SET LOCAL`` is transaction-scoped: the setting is cleared automatically
    when the transaction ends and the connection is returned to the pool,
    preventing cross-request context leakage.

    This dependency **replaces** :func:`app.core.database.get_session` on all
    authenticated routes.  Public routes (auth, health) continue to use
    :func:`~app.core.database.get_session` directly.

    Args:
        current_user: The authenticated user (validated by Bearer token).
        session: The active database session from :func:`get_session`.

    Yields:
        The same :class:`AsyncSession` after setting the RLS context variable.
    """
    # asyncpg does not support parameterised SET statements; the UUID is safe
    # to embed directly because it comes from the validated JWT / ORM model.
    uid = str(current_user.id)
    await session.execute(
        text(f"SET LOCAL app.current_user_id = '{uid}'")  # noqa: S608
    )
    yield session
