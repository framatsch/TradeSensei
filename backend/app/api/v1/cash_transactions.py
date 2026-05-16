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

"""API router for managing cash transactions.

This router handles endpoints related to non-trade cash flows (dividends, fees, etc.).
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import PAGINATION_DEFAULT_LIMIT, PAGINATION_MAX_LIMIT
from app.core.dependencies import require_portfolio_owner
from app.core.deps import get_current_user, get_session_with_rls
from app.core.exceptions import CashTransactionNotFoundError
from app.models.user import User
from app.schemas.cash_transaction import (
    CashTransactionCreateRequest,
    CashTransactionFilterParams,
    CashTransactionRead,
    CashTransactionUpdate,
)
from app.schemas.common import OffsetPage, ResponseEnvelope
from app.services.cash_transaction_service import CashTransactionService

router = APIRouter(
    prefix="/portfolios/{portfolio_id}/accounts/{account_id}/cash-transactions",
    tags=["Cash Transactions"],
    dependencies=[Depends(require_portfolio_owner)],
)


def _get_service(
    session: Annotated[AsyncSession, Depends(get_session_with_rls)],
) -> CashTransactionService:
    """Build a cash transaction service bound to the request session."""
    return CashTransactionService(session)


@router.post(
    "",
    response_model=ResponseEnvelope[CashTransactionRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create a cash transaction",
    description=("Record a new cash transaction (dividend, fee, deposit, etc.) for the account."),
)
async def create_cash_transaction(
    portfolio_id: uuid.UUID,
    account_id: uuid.UUID,
    create_request: CashTransactionCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CashTransactionService, Depends(_get_service)],
) -> ResponseEnvelope[CashTransactionRead]:
    """Create a new cash transaction."""
    transaction = await service.create(
        user_id=current_user.id,
        portfolio_id=portfolio_id,
        account_id=account_id,
        create_request=create_request,
    )
    return ResponseEnvelope(data=CashTransactionRead.model_validate(transaction))


@router.get(
    "",
    response_model=ResponseEnvelope[OffsetPage[CashTransactionRead]],
    summary="List cash transactions",
    description="Retrieve a paginated list of cash transactions for an account.",
)
async def list_cash_transactions(
    portfolio_id: uuid.UUID,
    account_id: uuid.UUID,
    filters: Annotated[CashTransactionFilterParams, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CashTransactionService, Depends(_get_service)],
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=PAGINATION_MAX_LIMIT,
            description="Maximum number of items to return.",
        ),
    ] = PAGINATION_DEFAULT_LIMIT,
    offset: Annotated[
        int,
        Query(
            ge=0,
            description="Number of items to skip before returning results.",
        ),
    ] = 0,
) -> ResponseEnvelope[OffsetPage[CashTransactionRead]]:
    """List cash transactions."""
    transactions, total_count = await service.list_by_account(
        user_id=current_user.id,
        portfolio_id=portfolio_id,
        account_id=account_id,
        filters=filters,
        limit=limit,
        offset=offset,
    )

    return ResponseEnvelope(
        data=OffsetPage(
            items=[CashTransactionRead.model_validate(t) for t in transactions],
            total=total_count,
            limit=limit,
            offset=offset,
        )
    )


@router.get(
    "/{transaction_id}",
    response_model=ResponseEnvelope[CashTransactionRead],
    summary="Get a cash transaction",
    description="Retrieve a specific cash transaction by its ID.",
)
async def get_cash_transaction(
    portfolio_id: uuid.UUID,
    account_id: uuid.UUID,
    transaction_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CashTransactionService, Depends(_get_service)],
) -> ResponseEnvelope[CashTransactionRead]:
    """Get a single cash transaction."""
    try:
        transaction = await service.get(
            user_id=current_user.id,
            portfolio_id=portfolio_id,
            account_id=account_id,
            transaction_id=transaction_id,
        )
    except CashTransactionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return ResponseEnvelope(data=CashTransactionRead.model_validate(transaction))


@router.patch(
    "/{transaction_id}",
    response_model=ResponseEnvelope[CashTransactionRead],
    summary="Update a cash transaction",
    description="Update fields of an existing cash transaction.",
)
async def update_cash_transaction(
    portfolio_id: uuid.UUID,
    account_id: uuid.UUID,
    transaction_id: uuid.UUID,
    update_request: CashTransactionUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CashTransactionService, Depends(_get_service)],
) -> ResponseEnvelope[CashTransactionRead]:
    """Update a cash transaction."""
    try:
        transaction = await service.update(
            user_id=current_user.id,
            portfolio_id=portfolio_id,
            account_id=account_id,
            transaction_id=transaction_id,
            update_schema=update_request,
        )
    except CashTransactionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return ResponseEnvelope(data=CashTransactionRead.model_validate(transaction))


@router.delete(
    "/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a cash transaction",
    description="Permanently delete a cash transaction.",
)
async def delete_cash_transaction(
    portfolio_id: uuid.UUID,
    account_id: uuid.UUID,
    transaction_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CashTransactionService, Depends(_get_service)],
) -> None:
    """Delete a cash transaction."""
    try:
        await service.delete(
            user_id=current_user.id,
            portfolio_id=portfolio_id,
            account_id=account_id,
            transaction_id=transaction_id,
        )
    except CashTransactionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
