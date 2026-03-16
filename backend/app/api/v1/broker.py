"""Route handlers for the Schwab live broker API integration.

Exposes OAuth 2.0 PKCE connect / callback flow, trade synchronisation,
connection status, and disconnection endpoints under ``/broker/schwab/``.
All endpoints (except the callback) require a valid Bearer token.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.core.deps import get_current_user
from app.core.exceptions import BrokerConnectionNotFoundError, ConfigurationError
from app.models.user import User
from app.schemas.broker import BrokerStatusResponse, SchwabSyncResult
from app.schemas.common import ResponseEnvelope
from app.services.broker_service import BrokerService

router = APIRouter(prefix="/broker", tags=["broker"])


def _get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BrokerService:
    """FastAPI dependency that constructs a :class:`BrokerService`.

    Args:
        session: Injected async database session.

    Returns:
        A :class:`BrokerService` bound to the current session.
    """
    return BrokerService(session)


@router.get(
    "/schwab/connect",
    summary="Initiate Schwab OAuth connection",
    description=(
        "Generates a Schwab OAuth 2.0 PKCE authorization URL and redirects the "
        "user to Schwab for authentication and consent."
    ),
    response_class=RedirectResponse,
    status_code=status.HTTP_302_FOUND,
)
async def connect_schwab(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[BrokerService, Depends(_get_service)],
) -> RedirectResponse:
    """Redirect the authenticated user to Schwab's OAuth authorization page.

    Generates a fresh PKCE pair and CSRF state token, stores them temporarily,
    and returns a redirect to Schwab's authorization endpoint.

    Args:
        current_user: The authenticated user, injected by ``get_current_user``.
        service: The :class:`BrokerService` instance.

    Returns:
        A :class:`~fastapi.responses.RedirectResponse` to the Schwab
        authorization URL.

    Raises:
        :class:`fastapi.HTTPException`: 503 if Schwab credentials are not
            configured.
    """
    try:
        auth_url = await service.get_schwab_connect_url(current_user.id)
    except ConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)


@router.get(
    "/schwab/callback",
    summary="Schwab OAuth callback",
    description=(
        "Receives the authorization code from Schwab, exchanges it for tokens, "
        "and redirects the user back to the frontend dashboard."
    ),
    response_class=RedirectResponse,
    status_code=status.HTTP_302_FOUND,
    include_in_schema=True,
)
async def schwab_callback(
    code: str,
    state: str,
    service: Annotated[BrokerService, Depends(_get_service)],
) -> RedirectResponse:
    """Handle the Schwab OAuth callback redirect.

    Exchanges the authorization code for OAuth tokens, encrypts them, and
    stores the connection.  Then redirects the user back to the frontend
    dashboard with ``?connected=true``.

    Args:
        code: The authorization code provided by Schwab in the callback URL.
        state: The CSRF state token echoed back by Schwab.
        service: The :class:`BrokerService` instance.

    Returns:
        A :class:`~fastapi.responses.RedirectResponse` to the frontend
        dashboard connections page.

    Raises:
        :class:`fastapi.HTTPException`: 400 if the state token is invalid.
        :class:`fastapi.HTTPException`: 503 if Schwab credentials are not
            configured.
    """
    try:
        await service.handle_schwab_callback(code=code, state=state)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    frontend_origin = (
        settings.cors_origins[0] if settings.cors_origins else "http://localhost:3000"
    )
    redirect_url = f"{frontend_origin}/dashboard/connections?connected=true"
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)


@router.post(
    "/schwab/sync",
    summary="Sync Schwab trades",
    description=(
        "Fetches recent orders from the Schwab API, normalises them, deduplicates "
        "by broker order ID, and imports new trades into the journal."
    ),
    response_model=ResponseEnvelope[SchwabSyncResult],
    status_code=status.HTTP_200_OK,
)
async def sync_schwab(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[BrokerService, Depends(_get_service)],
    days: int = 30,
) -> ResponseEnvelope[SchwabSyncResult]:
    """Trigger an incremental Schwab trade sync for the authenticated user.

    Args:
        current_user: The authenticated user.
        service: The :class:`BrokerService` instance.
        days: Number of past days to fetch orders for (default: 30).

    Returns:
        A :class:`~app.schemas.common.ResponseEnvelope` wrapping a
        :class:`~app.schemas.broker.SchwabSyncResult`.

    Raises:
        :class:`fastapi.HTTPException`: 404 if no Schwab connection exists.
        :class:`fastapi.HTTPException`: 503 if Schwab is not configured.
    """
    try:
        result = await service.sync_schwab_trades(
            user_id=current_user.id,
            days=days,
        )
    except BrokerConnectionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return ResponseEnvelope(data=result)


@router.get(
    "/schwab/status",
    summary="Get Schwab connection status",
    description=(
        "Returns whether the authenticated user has an active Schwab connection."
    ),
    response_model=ResponseEnvelope[BrokerStatusResponse],
    status_code=status.HTTP_200_OK,
)
async def get_schwab_status(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[BrokerService, Depends(_get_service)],
) -> ResponseEnvelope[BrokerStatusResponse]:
    """Return the Schwab connection status for the authenticated user.

    Args:
        current_user: The authenticated user.
        service: The :class:`BrokerService` instance.

    Returns:
        A :class:`~app.schemas.common.ResponseEnvelope` wrapping a
        :class:`~app.schemas.broker.BrokerStatusResponse`.
    """
    result = await service.get_schwab_status(current_user.id)
    return ResponseEnvelope(data=result)


@router.delete(
    "/schwab/disconnect",
    summary="Disconnect Schwab",
    description="Removes the stored Schwab OAuth tokens for the authenticated user.",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def disconnect_schwab(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[BrokerService, Depends(_get_service)],
) -> None:
    """Disconnect the Schwab integration for the authenticated user.

    Deletes the stored OAuth tokens.  After disconnecting, the user must
    re-authenticate via ``GET /broker/schwab/connect`` to sync trades again.

    Args:
        current_user: The authenticated user.
        service: The :class:`BrokerService` instance.

    Raises:
        :class:`fastapi.HTTPException`: 404 if no Schwab connection exists.
    """
    try:
        await service.disconnect_schwab(current_user.id)
    except BrokerConnectionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
