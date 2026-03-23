"""API router for managing cash transactions.

This router handles endpoints related to non-trade cash flows (dividends, fees, etc.).
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import PAGINATION_DEFAULT_LIMIT, PAGINATION_MAX_LIMIT
from app.core.database import get_session
from app.core.deps import get_current_user
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
    prefix="/accounts/{account_id}/cash-transactions", tags=["Cash Transactions"]
)


@router.post(
    "",
    response_model=ResponseEnvelope[CashTransactionRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create a cash transaction",
    description=(
        "Record a new cash transaction (dividend, fee, deposit, etc.) for the account."
    ),
)
async def create_cash_transaction(
    account_id: uuid.UUID,
    create_request: CashTransactionCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ResponseEnvelope[CashTransactionRead]:
    """Create a new cash transaction."""
    transaction = await CashTransactionService.create(
        session=session,
        user_id=current_user.id,
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
    account_id: uuid.UUID,
    filters: Annotated[CashTransactionFilterParams, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
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
    transactions, total_count = await CashTransactionService.list_by_account(
        session=session,
        user_id=current_user.id,
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
    account_id: uuid.UUID,
    transaction_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ResponseEnvelope[CashTransactionRead]:
    """Get a single cash transaction."""
    transaction = await CashTransactionService.get(
        session=session,
        user_id=current_user.id,
        account_id=account_id,
        transaction_id=transaction_id,
    )
    return ResponseEnvelope(data=CashTransactionRead.model_validate(transaction))


@router.patch(
    "/{transaction_id}",
    response_model=ResponseEnvelope[CashTransactionRead],
    summary="Update a cash transaction",
    description="Update fields of an existing cash transaction.",
)
async def update_cash_transaction(
    account_id: uuid.UUID,
    transaction_id: uuid.UUID,
    update_request: CashTransactionUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ResponseEnvelope[CashTransactionRead]:
    """Update a cash transaction."""
    transaction = await CashTransactionService.update(
        session=session,
        user_id=current_user.id,
        account_id=account_id,
        transaction_id=transaction_id,
        update_schema=update_request,
    )
    return ResponseEnvelope(data=CashTransactionRead.model_validate(transaction))


@router.delete(
    "/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a cash transaction",
    description="Permanently delete a cash transaction.",
)
async def delete_cash_transaction(
    account_id: uuid.UUID,
    transaction_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    """Delete a cash transaction."""
    await CashTransactionService.delete(
        session=session,
        user_id=current_user.id,
        account_id=account_id,
        transaction_id=transaction_id,
    )
