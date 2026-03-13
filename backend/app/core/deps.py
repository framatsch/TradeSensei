"""FastAPI dependencies for authentication and session management.

The :func:`get_current_user` dependency validates the Bearer token and
returns the active :class:`~app.models.user.User` ORM instance, raising
HTTP 401 when the token is invalid or the user is inactive.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
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
