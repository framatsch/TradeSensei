"""Route handlers for the ``/api/v1/auth`` endpoints.

Covers registration, OAuth2 password-flow token issuance,
token refresh via httpOnly cookie, and logout.
"""

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import REFRESH_TOKEN_EXPIRE_DAYS
from app.core.database import get_session
from app.core.deps import get_current_user
from app.core.exceptions import InvalidCredentialsError, UserAlreadyExistsError
from app.models.user import User
from app.schemas.auth import TokenResponse
from app.schemas.common import ResponseEnvelope
from app.schemas.user import UserCreate, UserLogin, UserRead
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

_REFRESH_COOKIE = "refresh_token"
_REFRESH_MAX_AGE = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60  # seconds


def _get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AuthService:
    """FastAPI dependency that constructs an :class:`AuthService`.

    Args:
        session: Injected async database session.

    Returns:
        An :class:`AuthService` bound to the current session.
    """
    return AuthService(session)


@router.post(
    "/register",
    response_model=ResponseEnvelope[UserRead],
    status_code=status.HTTP_201_CREATED,
    summary="Register a New User",
    description=(
        "Create a new user account with a unique username and email address. "
        "The plain-text password is **never** stored or returned — only its "
        "bcrypt hash is persisted in the database. "
        "After registration, obtain tokens via ``POST /auth/token``."
    ),
    response_description="The newly registered user wrapped in a response envelope.",
    responses={
        201: {"description": "User registered successfully."},
        409: {"description": "Username or email address is already taken."},
        422: {"description": "Request payload failed schema validation."},
    },
)
async def register(
    payload: UserCreate,
    service: Annotated[AuthService, Depends(_get_service)],
) -> ResponseEnvelope[UserRead]:
    """Register a new user account.

    Creates the user record after verifying the username and email are unique.
    The plain-text password is bcrypt-hashed before persistence and is never
    included in any response.

    Args:
        payload: Validated registration data (username, email, password).
        service: Injected auth service.

    Returns:
        A :class:`ResponseEnvelope` containing the created
        :class:`UserRead` DTO.

    Raises:
        HTTPException: 409 if the username or email is already registered.
    """
    try:
        user = await service.register(payload)
    except UserAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email address is already in use.",
        ) from exc
    return ResponseEnvelope[UserRead](data=UserRead.model_validate(user))


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Obtain Access and Refresh Tokens",
    description=(
        "Authenticate with username (or email) and password using the OAuth2 "
        "password flow (``application/x-www-form-urlencoded`` body). "
        "On success, returns a short-lived **access token** (15 min) in the "
        "response body and sets a long-lived **refresh token** (7 days) as an "
        "httpOnly Secure ``refresh_token`` cookie. "
        "Pass the access token in subsequent requests as "
        "``Authorization: Bearer <token>``."
    ),
    response_description=(
        "Access token in the response body; refresh token set as a cookie."
    ),
    responses={
        200: {"description": "Authentication successful."},
        401: {"description": "Incorrect username/email or password."},
        422: {"description": "Form body validation error (missing fields)."},
    },
)
async def login(
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: Annotated[AuthService, Depends(_get_service)],
) -> TokenResponse:
    """Issue access and refresh tokens for the supplied credentials.

    Accepts an OAuth2 ``application/x-www-form-urlencoded`` body with
    ``username`` and ``password`` fields. The ``username`` field accepts
    either the account username or email address.

    On success, the access token (15-minute lifetime) is returned in the
    response body. A long-lived refresh token (7-day lifetime) is written
    to an httpOnly Secure ``refresh_token`` cookie scoped to ``/api/v1/auth``.

    Args:
        response: FastAPI response object used to set the cookie.
        form_data: OAuth2 password form fields.
        service: Injected auth service.

    Returns:
        A :class:`TokenResponse` containing the short-lived access token.

    Raises:
        HTTPException: 401 if the username/email or password is incorrect.
    """
    try:
        access_token, refresh_token = await service.login(
            UserLogin(username=form_data.username, password=form_data.password)
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=_REFRESH_MAX_AGE,
        path="/api/v1/auth",
    )
    return TokenResponse(access_token=access_token)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh the Access Token",
    description=(
        "Exchange the long-lived ``refresh_token`` httpOnly cookie for a new "
        "short-lived access token and a rotated refresh token. The cookie must "
        "have been set by a previous call to ``POST /auth/token``. "
        "The refresh token is rotated on each call — the old token is invalidated "
        "and a new one is issued in its place."
    ),
    response_description="A fresh short-lived access token.",
    responses={
        200: {"description": "Token refreshed successfully."},
        401: {
            "description": (
                "Refresh token cookie is absent, has been tampered with, "
                "or has expired."
            )
        },
    },
)
async def refresh_token(
    response: Response,
    service: Annotated[AuthService, Depends(_get_service)],
    refresh_token_cookie: Annotated[str | None, Cookie(alias=_REFRESH_COOKIE)] = None,
) -> TokenResponse:
    """Issue a new access token and rotated refresh token using the cookie.

    Args:
        response: FastAPI response object used to set the rotated cookie.
        service: Injected auth service.
        refresh_token_cookie: The ``refresh_token`` httpOnly cookie value.

    Returns:
        A :class:`TokenResponse` containing the new access token.

    Raises:
        HTTPException: 401 if the cookie is absent, invalid, or expired.
    """
    if refresh_token_cookie is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        new_access_token, new_refresh_token = await service.refresh(
            refresh_token_cookie
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=new_refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=_REFRESH_MAX_AGE,
        path="/api/v1/auth",
    )
    return TokenResponse(access_token=new_access_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout — Clear the Refresh Token Cookie",
    description=(
        "Invalidate all refresh tokens for the authenticated user and clear "
        "the ``refresh_token`` httpOnly cookie, effectively logging the user "
        "out of any device that relies on this cookie for re-authentication. "
        "Requires a valid Bearer access token. "
        "Callers should also discard their in-memory access token."
    ),
    response_description="No content — the refresh token cookie has been cleared.",
    responses={
        204: {"description": "Cookie cleared. No content returned."},
        401: {"description": "Missing or invalid Bearer token."},
    },
)
async def logout(
    response: Response,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AuthService, Depends(_get_service)],
) -> None:
    """Invalidate refresh tokens and clear the refresh token cookie.

    Increments the user's token version counter so all previously issued
    refresh tokens are rejected, then deletes the cookie.

    Args:
        response: FastAPI response object used to delete the cookie.
        current_user: Injected authenticated user ORM instance.
        service: Injected auth service.
    """
    await service.logout(current_user)
    response.delete_cookie(
        key=_REFRESH_COOKIE,
        httponly=True,
        secure=True,
        samesite="strict",
        path="/api/v1/auth",
    )
