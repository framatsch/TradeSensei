"""Route handlers for the ``/api/v1/accounts`` resource.

Provides full CRUD on trading accounts, scoped to the authenticated user.
All endpoints require a valid Bearer token.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_portfolio_owner
from app.core.deps import get_current_user, get_session_with_rls
from app.core.exceptions import AccountNotFoundError
from app.models.user import User
from app.schemas.account import (
    AccountCreate,
    AccountMetrics,
    AccountRead,
    AccountUpdate,
)
from app.schemas.common import CursorPage, ResponseEnvelope
from app.services.account_service import AccountService

router = APIRouter(
    prefix="/portfolios/{portfolio_id}/accounts",
    tags=["accounts"],
    dependencies=[Depends(require_portfolio_owner)],
)


def _get_service(
    session: Annotated[AsyncSession, Depends(get_session_with_rls)],
) -> AccountService:
    """FastAPI dependency that constructs an :class:`AccountService`.

    Args:
        session: Injected async database session.

    Returns:
        An :class:`AccountService` bound to the current session.
    """
    return AccountService(session)


@router.get(
    "",
    response_model=ResponseEnvelope[CursorPage[AccountRead]],
    summary="List Trading Accounts",
    description=(
        "Return a cursor-paginated list of all trading accounts owned by the "
        "currently authenticated user, ordered by creation date descending. "
        "Accounts belonging to other users are never included in the response."
    ),
    response_description=("A paginated list of accounts wrapped in a response envelope, with a ``next_cursor`` token when further pages exist."),
    responses={
        200: {"description": "Account list returned successfully."},
        401: {"description": "Missing or invalid Bearer token."},
    },
)
async def list_accounts(
    portfolio_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AccountService, Depends(_get_service)],
) -> ResponseEnvelope[CursorPage[AccountRead]]:
    """Return all accounts for the authenticated user.

    Fetches every trading account scoped to the calling user's ID and
    wraps the results in a :class:`CursorPage`. Currently returns all
    accounts in a single page; cursor-based filtering will be wired in a
    future iteration.

    Args:
        current_user: Injected authenticated user ORM instance.
        service: Injected account service.

    Returns:
        A :class:`ResponseEnvelope` wrapping a :class:`CursorPage` of
        :class:`AccountRead` DTOs.
    """
    page = await service.list_accounts(current_user.id, portfolio_id)
    return ResponseEnvelope[CursorPage[AccountRead]](data=page)


@router.post(
    "",
    response_model=ResponseEnvelope[AccountRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create a Trading Account",
    description=(
        "Create a new trading account owned by the currently authenticated user. "
        "Each account tracks trades under a single broker and currency. "
        "A user may have multiple accounts (e.g. one per broker or strategy)."
    ),
    response_description="The newly created account wrapped in a response envelope.",
    responses={
        201: {"description": "Account created successfully."},
        401: {"description": "Missing or invalid Bearer token."},
        422: {"description": "Request payload failed schema validation."},
    },
)
async def create_account(
    portfolio_id: uuid.UUID,
    payload: AccountCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AccountService, Depends(_get_service)],
) -> ResponseEnvelope[AccountRead]:
    """Create a new trading account for the authenticated user.

    The account is automatically scoped to the calling user's ID; callers
    cannot create accounts on behalf of other users.

    Args:
        payload: Validated account creation data (name, broker, currency).
        current_user: Injected authenticated user ORM instance.
        service: Injected account service.

    Returns:
        A :class:`ResponseEnvelope` containing the created
        :class:`AccountRead` DTO.
    """
    account_payload = payload.model_copy(update={"portfolio_id": portfolio_id})
    account = await service.create_account(account_payload, current_user.id)
    return ResponseEnvelope[AccountRead](data=account)


@router.get(
    "/{account_id}",
    response_model=ResponseEnvelope[AccountRead],
    summary="Get a Trading Account",
    description=(
        "Retrieve the full details of a specific trading account by its UUID. "
        "Enforces ownership — returns 404 if the account does not exist **or** "
        "belongs to a different user, so as not to leak account IDs."
    ),
    response_description="The requested account wrapped in a response envelope.",
    responses={
        200: {"description": "Account found and returned."},
        401: {"description": "Missing or invalid Bearer token."},
        404: {"description": "Account not found (or owned by another user)."},
        422: {"description": "The supplied ``account_id`` is not a valid UUID."},
    },
)
async def get_account(
    portfolio_id: uuid.UUID,
    account_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AccountService, Depends(_get_service)],
) -> ResponseEnvelope[AccountRead]:
    """Retrieve a single account owned by the authenticated user.

    The service layer enforces user scoping — an ``AccountNotFoundError`` is
    raised (and translated to HTTP 404) if the account does not exist or
    belongs to a different user.

    Args:
        account_id: UUID path parameter identifying the account.
        current_user: Injected authenticated user ORM instance.
        service: Injected account service.

    Returns:
        A :class:`ResponseEnvelope` containing the :class:`AccountRead` DTO.

    Raises:
        HTTPException: 404 if the account is not found for this user.
    """
    try:
        account = await service.get_account(account_id, current_user.id, portfolio_id)
    except AccountNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found.") from exc
    return ResponseEnvelope[AccountRead](data=account)


@router.patch(
    "/{account_id}",
    response_model=ResponseEnvelope[AccountRead],
    summary="Update a Trading Account",
    description=(
        "Apply a partial update to a trading account owned by the authenticated "
        "user. Only fields present in the request body are modified; omitted "
        "fields retain their current values. "
        "Returns 404 if the account does not exist or belongs to a different user."
    ),
    response_description=("The account after applying the partial update, wrapped in a response envelope."),
    responses={
        200: {"description": "Account updated successfully."},
        401: {"description": "Missing or invalid Bearer token."},
        404: {"description": "Account not found (or owned by another user)."},
        422: {"description": "Request payload failed schema validation."},
    },
)
async def update_account(
    portfolio_id: uuid.UUID,
    account_id: uuid.UUID,
    payload: AccountUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AccountService, Depends(_get_service)],
) -> ResponseEnvelope[AccountRead]:
    """Partially update a trading account owned by the authenticated user.

    Only the fields present in the request body are written. Fields that
    are absent (or explicitly ``None``) are not changed. Ownership is
    enforced — accounts belonging to other users raise HTTP 404.

    Args:
        account_id: UUID path parameter identifying the account.
        payload: Partial update data (name, broker, currency, is_active).
        current_user: Injected authenticated user ORM instance.
        service: Injected account service.

    Returns:
        A :class:`ResponseEnvelope` containing the updated
        :class:`AccountRead` DTO.

    Raises:
        HTTPException: 404 if the account is not found for this user.
    """
    try:
        account = await service.update_account(
            account_id,
            payload,
            current_user.id,
            portfolio_id,
        )
    except AccountNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found.") from exc
    return ResponseEnvelope[AccountRead](data=account)


@router.delete(
    "/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a Trading Account",
    description=(
        "Permanently delete a trading account and all its associated trades. "
        "**This operation is irreversible.** "
        "Returns 404 if the account does not exist or belongs to a different "
        "user, so as not to leak account IDs."
    ),
    response_description="No content — the account and its trades have been deleted.",
    responses={
        204: {"description": "Account and associated trades deleted."},
        401: {"description": "Missing or invalid Bearer token."},
        404: {"description": "Account not found (or owned by another user)."},
        422: {"description": "The supplied ``account_id`` is not a valid UUID."},
    },
)
async def delete_account(
    portfolio_id: uuid.UUID,
    account_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AccountService, Depends(_get_service)],
) -> None:
    """Delete a trading account owned by the authenticated user.

    Cascades the deletion to all trades associated with the account.
    Ownership is enforced — accounts belonging to other users raise
    HTTP 404 rather than HTTP 403, to avoid leaking account IDs.

    Args:
        account_id: UUID path parameter identifying the account.
        current_user: Injected authenticated user ORM instance.
        service: Injected account service.

    Raises:
        HTTPException: 404 if the account is not found for this user.
    """
    try:
        await service.delete_account(account_id, current_user.id, portfolio_id)
    except AccountNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found.",
        ) from exc


@router.get(
    "/{account_id}/metrics",
    response_model=ResponseEnvelope[AccountMetrics],
    summary="Get Account Cash Metrics",
    description=("Calculate and return aggregate cash metrics (e.g. total dividends and withholding tax) for the specified account."),
    response_description="Aggregate metrics wrapped in a response envelope.",
    responses={
        200: {"description": "Metrics calculated successfully."},
        401: {"description": "Missing or invalid Bearer token."},
        404: {"description": "Account not found (or owned by another user)."},
    },
)
async def get_account_metrics(
    portfolio_id: uuid.UUID,
    account_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AccountService, Depends(_get_service)],
) -> ResponseEnvelope[AccountMetrics]:
    """Retrieve aggregate cash metrics for the account.

    Args:
        account_id: UUID of the account.
        current_user: Authenticated user.
        service: Account service.

    Returns:
        ResponseEnvelope containing an AccountMetrics DTO.
    """
    try:
        metrics = await service.get_metrics(account_id, current_user.id, portfolio_id)
        return ResponseEnvelope[AccountMetrics](data=metrics)
    except AccountNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found.") from exc
