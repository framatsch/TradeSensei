"""Route handlers for the ``/api/v1/auth`` endpoints.

Covers registration, OAuth2 password-flow token issuance,
token refresh via httpOnly cookie, logout, Google OAuth, and
self-service password reset via email.
"""

import contextlib
import logging
from typing import Annotated

from authlib.integrations.starlette_client import (  # type: ignore[import-untyped]
    OAuth,
    OAuthError,
)
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import REFRESH_TOKEN_EXPIRE_DAYS
from app.core.database import get_session
from app.core.deps import get_current_user
from app.core.email import send_password_reset_email
from app.core.exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
)
from app.core.security import (
    consume_password_reset_token,
    create_password_reset_token,
    hash_password,
)
from app.models.user import User
from app.schemas.auth import (
    AuthConfigResponse,
    ForgotPasswordRequest,
    OAuthExchangeRequest,
    OIDCConfig,
    ResetPasswordRequest,
    TokenResponse,
)
from app.schemas.common import ResponseEnvelope
from app.schemas.user import UserCreate, UserLogin, UserRead
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

_REFRESH_COOKIE = "refresh_token"
_REFRESH_MAX_AGE = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60  # seconds

# ---------------------------------------------------------------------------
# External Auth Clients (authlib)
# ---------------------------------------------------------------------------

_oauth = OAuth()
_oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

if settings.oidc_enabled and settings.oidc_configuration_url:
    _oauth.register(
        name="oidc",
        client_id=settings.oidc_client_id,
        client_secret=settings.oidc_client_secret,
        server_metadata_url=settings.oidc_configuration_url,
        client_kwargs={"scope": "openid email profile"},
    )


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


@router.get(
    "/config",
    response_model=AuthConfigResponse,
    summary="Get Authentication Configuration",
    description="Returns the available authentication methods enabled on the backend.",
    responses={
        200: {"description": "Configuration returned successfully."},
    },
)
async def get_config() -> AuthConfigResponse:
    """Return enabled authentication methods.

    Returns:
        An :class:`AuthConfigResponse` indicating which providers are active.
    """
    google_enabled = bool(settings.google_client_id and settings.google_client_secret)
    oidc_active = settings.oidc_enabled and bool(settings.oidc_configuration_url)
    any_external_provider = google_enabled or oidc_active
    if settings.local_auth_disabled and not any_external_provider:
        logger.warning(
            "LOCAL_AUTH_DISABLED=true but no external provider is configured — "
            "ignoring flag to prevent lockout."
        )
    local_auth_enabled = not (settings.local_auth_disabled and any_external_provider)
    return AuthConfigResponse(
        google_enabled=google_enabled,
        oidc=OIDCConfig(
            enabled=settings.oidc_enabled,
            provider_name=settings.oidc_provider_name,
        ),
        local_auth_enabled=local_auth_enabled,
        password_reset_enabled=settings.password_reset_enabled,
    )


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


# ---------------------------------------------------------------------------
# Google OAuth routes
# ---------------------------------------------------------------------------

_FRONTEND_CALLBACK_URL = f"{settings.frontend_url.rstrip('/')}/auth/callback"
_FRONTEND_LOGIN_URL = f"{settings.frontend_url.rstrip('/')}/login"


@router.get(
    "/google",
    summary="Initiate Google OAuth Login",
    description=(
        "Redirects the browser to Google's OAuth 2.0 authorization page. "
        "The user will be asked to grant access to their Google profile and "
        "email. After consent, Google redirects back to ``GET /auth/google/callback``."
    ),
    response_description="HTTP 302 redirect to Google's authorization URL.",
    status_code=status.HTTP_302_FOUND,
    responses={
        302: {"description": "Redirect to Google authorization URL."},
        503: {"description": "Google OAuth is not configured."},
    },
    include_in_schema=True,
)
async def google_login(request: Request) -> RedirectResponse:
    """Redirect the browser to Google's OAuth authorization page.

    Args:
        request: The incoming FastAPI request (needed for session state).

    Returns:
        A :class:`RedirectResponse` pointing to Google's authorization URL.

    Raises:
        HTTPException: 503 if ``GOOGLE_CLIENT_ID`` is not configured.
    """
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured.",
        )
    redirect_uri = settings.google_redirect_uri
    return await _oauth.google.authorize_redirect(request, redirect_uri)  # type: ignore[no-any-return]


@router.get(
    "/google/callback",
    summary="Google OAuth Callback",
    description=(
        "Receives the authorization code from Google after user consent. "
        "Exchanges the code for an ID token, provisions or retrieves the "
        "local user, sets the ``refresh_token`` httpOnly cookie, and "
        "redirects the browser to the frontend callback page with a "
        "short-lived one-time token in the query string."
    ),
    response_description=(
        "HTTP 302 redirect to the frontend callback page with ``?token=``."
    ),
    status_code=status.HTTP_302_FOUND,
    responses={
        302: {"description": "Redirect to frontend with one-time token or error."},
    },
    include_in_schema=True,
)
async def google_callback(
    request: Request,
    response: Response,
    service: Annotated[AuthService, Depends(_get_service)],
) -> RedirectResponse:
    """Handle the Google OAuth callback and issue JWT tokens.

    Validates the authorization code, retrieves the Google user info,
    provisions or links the local account, sets the refresh token cookie,
    and redirects to the frontend with a one-time exchange token.

    Args:
        request: The incoming FastAPI request (contains OAuth state).
        response: FastAPI response object — used to set the refresh cookie.
        service: Injected auth service.

    Returns:
        A :class:`RedirectResponse` to the frontend callback page.
    """
    try:
        token = await _oauth.google.authorize_access_token(request)
    except OAuthError:
        redirect = RedirectResponse(
            url=f"{_FRONTEND_LOGIN_URL}?error=oauth_cancelled",
            status_code=status.HTTP_302_FOUND,
        )
        return redirect

    user_info = token.get("userinfo")
    if not user_info:
        redirect = RedirectResponse(
            url=f"{_FRONTEND_LOGIN_URL}?error=oauth_failed",
            status_code=status.HTTP_302_FOUND,
        )
        return redirect

    try:
        (
            access_token,
            refresh_token,
            one_time_token,
        ) = await service.external_oauth_login(
            provider="google",
            provider_sub=str(user_info["sub"]),
            email=str(user_info["email"]),
            display_name=str(user_info.get("name", user_info.get("email", "user"))),
            email_verified=bool(user_info.get("email_verified", False)),
        )
    except InvalidCredentialsError:
        redirect = RedirectResponse(
            url=f"{_FRONTEND_LOGIN_URL}?error=oauth_failed",
            status_code=status.HTTP_302_FOUND,
        )
        return redirect

    redirect = RedirectResponse(
        url=f"{_FRONTEND_CALLBACK_URL}?token={one_time_token}",
        status_code=status.HTTP_302_FOUND,
    )
    redirect.set_cookie(
        key=_REFRESH_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",  # Must be lax (not strict) for cross-site OAuth redirects
        max_age=_REFRESH_MAX_AGE,
        path="/api/v1/auth",
    )
    return redirect


@router.post(
    "/google/exchange",
    response_model=TokenResponse,
    summary="Exchange One-Time OAuth Token",
    description=(
        "Exchange the short-lived one-time token received from the OAuth "
        "callback redirect URL for a full JWT access token. "
        "The one-time token is valid for 60 seconds and can only be used once. "
        "The refresh token is already set as an httpOnly cookie by the callback."
    ),
    response_description="Access token in the response body.",
    responses={
        200: {"description": "Token exchange successful."},
        401: {"description": "One-time token is invalid, expired, or already used."},
        422: {"description": "Request body validation error."},
    },
)
async def google_exchange(
    payload: OAuthExchangeRequest,
    service: Annotated[AuthService, Depends(_get_service)],
) -> TokenResponse:
    """Exchange a one-time OAuth token for an access token.

    Args:
        payload: Request body containing the one-time token.
        service: Injected auth service.

    Returns:
        A :class:`TokenResponse` containing the access token.

    Raises:
        HTTPException: 401 if the one-time token is invalid or already used.
    """
    try:
        access_token, _ = await service.exchange_one_time_token(payload.one_time_token)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired one-time token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return TokenResponse(access_token=access_token)


# ---------------------------------------------------------------------------
# Password reset routes
# ---------------------------------------------------------------------------

_FORGOT_PASSWORD_RESPONSE = (
    "If an account with that email exists, a reset link has been sent."
)


@router.post(
    "/forgot-password",
    status_code=status.HTTP_200_OK,
    summary="Request a Password Reset Email",
    description=(
        "Sends a password-reset link to the provided email address if a local "
        "account with that email exists. Always returns 200 to prevent user "
        "enumeration — callers cannot distinguish known from unknown addresses."
    ),
    responses={
        200: {"description": "Request processed (email may have been sent)."},
        503: {"description": "Password reset is not configured on this server."},
    },
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    service: Annotated[AuthService, Depends(_get_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    """Trigger a password-reset email for the given address.

    Always returns the same message regardless of whether the email is
    registered, to avoid leaking account existence information.

    Args:
        payload: Request body containing the email address.
        service: Injected auth service.
        session: Injected async database session (for token replay check).

    Returns:
        A dict with a ``detail`` message.

    Raises:
        HTTPException: 503 if SMTP is not configured.
    """
    if not settings.password_reset_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Password reset is not configured.",
        )

    user = await service.get_user_by_email(payload.email)
    if user is not None and user.hashed_password is not None:
        token = create_password_reset_token(user.id)
        reset_url = f"{settings.frontend_url.rstrip('/')}/reset-password?token={token}"
        await send_password_reset_email(user.email, reset_url)

    return {"detail": _FORGOT_PASSWORD_RESPONSE}


@router.post(
    "/reset-password",
    status_code=status.HTTP_200_OK,
    summary="Reset Password via Token",
    description=(
        "Validates the password-reset token from the email link, sets the new "
        "password, and invalidates all existing sessions for the user."
    ),
    responses={
        200: {"description": "Password updated successfully."},
        401: {"description": "Token is invalid, expired, or already used."},
        422: {"description": "Validation error (e.g. password too short)."},
    },
)
async def reset_password(
    payload: ResetPasswordRequest,
    service: Annotated[AuthService, Depends(_get_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    """Set a new password using a valid password-reset token.

    Consumes the token (single-use), hashes the new password, persists it,
    and increments ``refresh_token_version`` to invalidate all active sessions.

    Args:
        payload: Request body with the reset token and new password.
        service: Injected auth service.
        session: Injected async database session.

    Returns:
        A dict with a ``detail`` confirmation message.

    Raises:
        HTTPException: 401 if the token is invalid, expired, or already used.
    """
    try:
        user_id = await consume_password_reset_token(payload.token, session)
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Reset link has expired or has already been used.",
        ) from exc

    await service.update_password(user_id, hash_password(payload.new_password))
    return {"detail": "Password updated successfully."}


# ---------------------------------------------------------------------------
# Generic OIDC routes
# ---------------------------------------------------------------------------


@router.get(
    "/oidc",
    summary="Initiate OIDC Login",
    description="Redirects the browser to the configured OIDC authorization page.",
    response_description="HTTP 302 redirect to the OIDC authorization URL.",
    status_code=status.HTTP_302_FOUND,
    responses={
        302: {"description": "Redirect to OIDC authorization URL."},
        503: {"description": "OIDC is not configured or enabled."},
    },
    include_in_schema=True,
)
async def oidc_login(request: Request) -> RedirectResponse:
    """Redirect the browser to OIDC authorization page.

    Args:
        request: The incoming FastAPI request.

    Returns:
        A :class:`RedirectResponse` pointing to OIDC authorization URL.

    Raises:
        HTTPException: 503 if OIDC is not configured.
    """
    if not settings.oidc_enabled or "oidc" not in _oauth._clients:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OIDC is not configured or enabled.",
        )
    redirect_uri = settings.oidc_redirect_uri
    return await _oauth.oidc.authorize_redirect(request, redirect_uri)  # type: ignore[no-any-return]


@router.get(
    "/oidc/callback",
    summary="OIDC Callback",
    description="Handles the OIDC callback, issues JWTs, and redirects to frontend.",
    response_description="HTTP 302 redirect to the frontend callback page.",
    status_code=status.HTTP_302_FOUND,
    responses={
        302: {"description": "Redirect to frontend with one-time token or error."},
    },
    include_in_schema=True,
)
async def oidc_callback(
    request: Request,
    response: Response,
    service: Annotated[AuthService, Depends(_get_service)],
) -> RedirectResponse:
    """Handle the OIDC callback and issue JWT tokens."""
    try:
        token = await _oauth.oidc.authorize_access_token(request)
    except OAuthError:
        return RedirectResponse(
            url=f"{_FRONTEND_LOGIN_URL}?error=oauth_cancelled",
            status_code=status.HTTP_302_FOUND,
        )

    user_info = token.get("userinfo")
    if not user_info:
        # Try to fetch userinfo explicitly if not in token
        with contextlib.suppress(Exception):
            user_info = await _oauth.oidc.userinfo(token=token)

    if not user_info:
        return RedirectResponse(
            url=f"{_FRONTEND_LOGIN_URL}?error=oauth_failed",
            status_code=status.HTTP_302_FOUND,
        )

    # Some providers use "preferred_username" or "name", some don't have email_verified
    sub = str(user_info["sub"])
    email = str(user_info.get("email", f"{sub}@oidc.local"))
    display_name = str(
        user_info.get("preferred_username")
        or user_info.get("name")
        or user_info.get("email")
        or "user"
    )

    # For internal OIDC (like Authentik), we often want to trust the email
    # even if the provider hasn't explicitly flagged it as "verified" in the UI.
    email_verified = True

    try:
        (
            access_token,
            refresh_token,
            one_time_token,
        ) = await service.external_oauth_login(
            provider="oidc",
            provider_sub=sub,
            email=email,
            display_name=display_name,
            email_verified=email_verified,
        )
    except InvalidCredentialsError:
        return RedirectResponse(
            url=f"{_FRONTEND_LOGIN_URL}?error=oauth_failed",
            status_code=status.HTTP_302_FOUND,
        )

    redirect = RedirectResponse(
        url=f"{_FRONTEND_CALLBACK_URL}?token={one_time_token}",
        status_code=status.HTTP_302_FOUND,
    )
    redirect.set_cookie(
        key=_REFRESH_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=_REFRESH_MAX_AGE,
        path="/api/v1/auth",
    )
    return redirect


@router.post(
    "/oidc/exchange",
    response_model=TokenResponse,
    summary="Exchange One-Time OIDC Token",
    description="Exchange short-lived token for access token (like Google exchange).",
)
async def oidc_exchange(
    payload: OAuthExchangeRequest,
    service: Annotated[AuthService, Depends(_get_service)],
) -> TokenResponse:
    """Exchange a one-time OIDC token for an access token."""
    try:
        access_token, _ = await service.exchange_one_time_token(payload.one_time_token)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired one-time token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return TokenResponse(access_token=access_token)
