"""Route handlers for account-centric broker sync operations.

Exposes a single ``POST /broker/sync/{account_id}`` endpoint that dispatches
a live trade synchronisation for the given account based on its
:attr:`~app.models.account.AccountType`.  All endpoints require a valid
Bearer token.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.deps import get_current_user
from app.core.exceptions import AccountNotFoundError, ConfigurationError
from app.models.user import User
from app.schemas.broker import BrokerSyncResult
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
    days: int = 30,
    from_date: str | None = None,
    overwrite_manually_edited: bool = False,
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
