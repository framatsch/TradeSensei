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

"""Route handlers for account-centric broker sync operations.

Exposes a single ``POST /broker/sync/{account_id}`` endpoint that dispatches
a live trade synchronisation for the given account based on its
:attr:`~app.models.account.AccountType`.  All endpoints require a valid
Bearer token.
"""

from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.deps import get_current_user, get_session_with_rls
from app.core.exceptions import AccountNotFoundError, ConfigurationError
from app.models.user import User
from app.schemas.broker import (
    BrokerStatusResponse,
    BrokerSyncResult,
    SchwabAuthorizeResponse,
    SchwabCompleteRequest,
)
from app.schemas.common import ResponseEnvelope
from app.services.broker_service import BrokerService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/broker", tags=["broker"])


def _get_service(
    session: Annotated[AsyncSession, Depends(get_session_with_rls)],
) -> BrokerService:
    """FastAPI dependency that constructs a :class:`BrokerService`.

    Args:
        session: Injected async database session.

    Returns:
        A :class:`BrokerService` bound to the current session.
    """
    return BrokerService(session)


def _get_service_public(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BrokerService:
    """Service dependency for unauthenticated endpoints."""
    return BrokerService(session)


@router.post(
    "/sync/{account_id}",
    summary="Sync broker trades for an account",
    description=(
        "Fetches recent orders from the broker API associated with the given "
        "account, normalises them, deduplicates by broker order ID, and imports "
        "new trades into the journal. "
        "The account must have type ``schwab`` or ``ibkr`` and the corresponding "
        "API credentials stored via the accounts API."
    ),
    response_model=ResponseEnvelope[BrokerSyncResult],
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Sync completed; result contains import counts."},
        400: {"description": "Account type is MANUAL — no API sync supported."},
        401: {"description": "Missing or invalid Bearer token."},
        404: {"description": "Account not found (or owned by another user)."},
    },
)
async def sync_account(
    account_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[BrokerService, Depends(_get_service)],
    days: Annotated[
        int,
        Query(description="Number of past days to include when from_date is omitted."),
    ] = 30,
    from_date: Annotated[
        str | None,
        Query(description="Optional YYYYMMDD start date that overrides days."),
    ] = None,
    overwrite_manually_edited: Annotated[
        bool,
        Query(description="When true, overwrite trades marked as manually edited."),
    ] = False,
) -> ResponseEnvelope[BrokerSyncResult]:
    """Trigger an incremental broker trade sync for the given account.

    Dispatches synchronisation based on the account's broker type.  The
    account must belong to the authenticated user; a different user's account
    UUID returns HTTP 404 to prevent account-ID enumeration.

    Args:
        account_id: UUID path parameter identifying the account to sync.
        current_user: The authenticated user.
        service: The :class:`BrokerService` instance.
        days: Number of past days to fetch orders for (default: 30).
            For IBKR accounts this is overridden by ``from_date`` when
            that parameter is provided.
        from_date: Optional explicit start date in ``YYYYMMDD`` format.
            When supplied for IBKR Flex sync, this takes precedence over
            ``days``.
        overwrite_manually_edited: When ``True``, trades that have been
            manually edited are overwritten instead of skipped.

    Returns:
        A :class:`~app.schemas.common.ResponseEnvelope` wrapping a
        :class:`~app.schemas.broker.BrokerSyncResult`.

    Raises:
        HTTPException: 404 if the account is not found for this user.
        HTTPException: 400 if the account type is MANUAL.
    """
    try:
        result = await service.sync_account(
            account_id=account_id,
            user_id=current_user.id,
            days=days,
            from_date=from_date,
            overwrite_manually_edited=overwrite_manually_edited,
        )
    except AccountNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return ResponseEnvelope(data=result)


@router.post(
    "/schwab/authorize/{account_id}",
    summary="Start Schwab OAuth authorization",
    description=(
        "Generates PKCE/state correlation records for a Schwab account and returns the Schwab authorization URL. Requires Bearer auth and account ownership."
    ),
    response_model=ResponseEnvelope[SchwabAuthorizeResponse],
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Authorization URL generated."},
        400: {"description": "Invalid Schwab OAuth configuration or missing account app credentials."},
        401: {"description": "Missing or invalid Bearer token."},
        404: {"description": "Account not found (or owned by another user)."},
    },
)
async def start_schwab_authorization(
    account_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[BrokerService, Depends(_get_service)],
) -> ResponseEnvelope[SchwabAuthorizeResponse]:
    try:
        authorization_url = await service.start_schwab_authorization(account_id=account_id, user_id=current_user.id)
    except AccountNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ResponseEnvelope(data=SchwabAuthorizeResponse(authorization_url=authorization_url))


@router.post(
    "/schwab/complete/{account_id}",
    summary="Complete Schwab OAuth with pasted redirect URL",
    description=("Completes Schwab OAuth for paste mode by parsing code/state from a pasted redirect URL, exchanging the code, and storing encrypted tokens."),
    response_model=ResponseEnvelope[BrokerStatusResponse],
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Schwab account connected."},
        400: {"description": "Invalid redirect URL, state mismatch, or exchange failure."},
        401: {"description": "Missing or invalid Bearer token."},
        404: {"description": "Account not found (or owned by another user)."},
    },
)
async def complete_schwab_connection(
    account_id: uuid.UUID,
    payload: SchwabCompleteRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[BrokerService, Depends(_get_service)],
) -> ResponseEnvelope[BrokerStatusResponse]:
    try:
        await service.complete_schwab_connection(
            account_id=account_id,
            user_id=current_user.id,
            redirect_url=payload.redirect_url,
        )
        status_payload = await service.get_schwab_status(account_id=account_id, user_id=current_user.id)
    except AccountNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ResponseEnvelope(data=status_payload)


@router.get(
    "/schwab/callback",
    summary="Schwab OAuth callback (unauthenticated)",
    description=(
        "Receives Schwab callback query parameters (code/state) without Bearer auth, "
        "resolves the account via stored state correlation, exchanges/stores tokens, "
        "and returns an HTML response instructing the user to close the tab."
    ),
    include_in_schema=True,
    response_class=HTMLResponse,
    responses={
        200: {"description": "HTML page instructing the user to close the tab."},
    },
)
async def schwab_callback(
    service: Annotated[BrokerService, Depends(_get_service_public)],
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
) -> HTMLResponse:
    if not code or not state:
        return HTMLResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content="<h1>Invalid request. Missing code or state. Please retry authorization.</h1>",
        )

    try:
        await service.complete_schwab_callback(code=code, state=state)
        return HTMLResponse(
            status_code=status.HTTP_200_OK,
            content="<h1>Authorization successful. You may close this tab.</h1>",
        )
    except Exception:
        logger.exception("Schwab callback failed")
        return HTMLResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content="<h1>Authorization failed. Please retry.</h1>",
        )


@router.get(
    "/schwab/status/{account_id}",
    summary="Get Schwab OAuth connection status",
    description="Returns whether the Schwab account currently has stored OAuth access/refresh tokens.",
    response_model=ResponseEnvelope[BrokerStatusResponse],
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Current Schwab connection status."},
        401: {"description": "Missing or invalid Bearer token."},
        404: {"description": "Account not found (or owned by another user)."},
    },
)
async def get_schwab_status(
    account_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[BrokerService, Depends(_get_service)],
) -> ResponseEnvelope[BrokerStatusResponse]:
    try:
        status_payload = await service.get_schwab_status(account_id=account_id, user_id=current_user.id)
    except AccountNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ResponseEnvelope(data=status_payload)


@router.delete(
    "/schwab/connect/{account_id}",
    summary="Disconnect Schwab OAuth connection",
    description=("Deletes stored Schwab OAuth token properties for the account and emits a broker.schwab_disconnected audit event."),
    response_model=ResponseEnvelope[BrokerStatusResponse],
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Schwab disconnected."},
        401: {"description": "Missing or invalid Bearer token."},
        404: {"description": "Account not found (or owned by another user)."},
    },
)
async def disconnect_schwab(
    account_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[BrokerService, Depends(_get_service)],
) -> ResponseEnvelope[BrokerStatusResponse]:
    try:
        await service.disconnect_schwab(account_id=account_id, user_id=current_user.id)
        status_payload = await service.get_schwab_status(account_id=account_id, user_id=current_user.id)
    except AccountNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ResponseEnvelope(data=status_payload)
