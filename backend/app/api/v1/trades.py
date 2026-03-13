"""Route handlers for the ``/api/v1/trades`` resource."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    PAGINATION_DEFAULT_LIMIT,
    PAGINATION_MAX_LIMIT,
    PAGINATION_MIN_LIMIT,
)
from app.core.database import get_session
from app.core.deps import get_current_user
from app.core.exceptions import InvalidCursorError, TradeNotFoundError
from app.models.user import User
from app.schemas.common import CursorPage, ResponseEnvelope
from app.schemas.trade import TradeCreate, TradeRead, TradeUpdate
from app.services.trade_service import TradeService

router = APIRouter(prefix="/trades", tags=["trades"])


def _get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TradeService:
    """FastAPI dependency that constructs a :class:`TradeService`.

    Args:
        session: Injected async database session.

    Returns:
        A :class:`TradeService` bound to the current session.
    """
    return TradeService(session)


@router.post(
    "",
    response_model=ResponseEnvelope[TradeRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new trade",
    description=(
        "Persist a new trading position. The trade may be open (no `exit_price` "
        "or `closed_at`) or already closed. The `pnl` field can be supplied "
        "manually; automated computation is planned for a later iteration."
    ),
    response_description="The newly created trade wrapped in a response envelope.",
    responses={
        201: {"description": "Trade created successfully."},
        422: {"description": "Request payload failed validation."},
    },
)
async def create_trade(
    payload: TradeCreate,
    service: Annotated[TradeService, Depends(_get_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ResponseEnvelope[TradeRead]:
    """Create and persist a new trading position.

    Args:
        payload: Validated trade creation data.
        service: Injected trade service.
        current_user: Injected authenticated user (required but unused until
            full account-scoping is added in a later iteration).

    Returns:
        A :class:`ResponseEnvelope` containing the created
        :class:`TradeRead` DTO.

    Raises:
        HTTPException: 422 if the payload fails Pydantic validation.
    """
    trade = await service.create_trade(payload)
    return ResponseEnvelope[TradeRead](data=trade)


@router.get(
    "",
    response_model=ResponseEnvelope[CursorPage[TradeRead]],
    summary="List trades (cursor-paginated)",
    description=(
        "Return a cursor-paginated list of trades ordered by `opened_at` "
        "descending. Pass the `next_cursor` value from the previous response "
        "as the `cursor` query parameter to fetch the next page. Omit `cursor` "
        "to start from the beginning."
    ),
    response_description=(
        "A page of trades wrapped in a response envelope, including a "
        "`next_cursor` token and optional total count."
    ),
    responses={
        200: {"description": "Paginated list of trades."},
        400: {"description": "Cursor token is malformed or expired."},
        422: {"description": "Query parameter validation error."},
    },
)
async def list_trades(
    service: Annotated[TradeService, Depends(_get_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    cursor: Annotated[str | None, Query(description="Opaque pagination cursor")] = None,
    limit: Annotated[
        int,
        Query(
            ge=PAGINATION_MIN_LIMIT,
            le=PAGINATION_MAX_LIMIT,
            description="Number of items per page",
        ),
    ] = PAGINATION_DEFAULT_LIMIT,
    include_total: Annotated[
        bool,
        Query(
            description=(
                "When true, include the total row count across all pages. "
                "Adds a COUNT(*) query; omit for best performance."
            )
        ),
    ] = False,
    account_id: Annotated[
        uuid.UUID | None,
        Query(description="Filter trades by account UUID"),
    ] = None,
) -> ResponseEnvelope[CursorPage[TradeRead]]:
    """Return a cursor-paginated list of trades ordered by ``opened_at`` descending.

    Args:
        service: Injected trade service.
        current_user: Injected authenticated user (passed through for future isolation).
        cursor: Optional opaque cursor token from a previous response.
        limit: Number of items to return (1–100, default 20).
        include_total: When ``True``, include the total row count.
        account_id: Optional UUID to filter trades by account.

    Returns:
        A :class:`ResponseEnvelope` wrapping a :class:`CursorPage` of
        :class:`TradeRead` DTOs.

    Raises:
        HTTPException: 400 if the cursor token is malformed.
    """
    try:
        page = await service.list_trades(
            limit=limit,
            cursor=cursor,
            include_total=include_total,
            account_id=account_id,
        )
    except InvalidCursorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ResponseEnvelope[CursorPage[TradeRead]](data=page)


@router.get(
    "/{trade_id}",
    response_model=ResponseEnvelope[TradeRead],
    summary="Get a single trade",
    description=(
        "Retrieve the full details of a single trade by its UUID. "
        "Returns 404 if no trade with the supplied ID exists."
    ),
    response_description="The requested trade wrapped in a response envelope.",
    responses={
        200: {"description": "Trade found and returned."},
        404: {"description": "Trade not found."},
        422: {"description": "The supplied trade_id is not a valid UUID."},
    },
)
async def get_trade(
    trade_id: uuid.UUID,
    service: Annotated[TradeService, Depends(_get_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ResponseEnvelope[TradeRead]:
    """Retrieve a single trade by its UUID.

    Args:
        trade_id: UUID path parameter.
        service: Injected trade service.
        current_user: Injected authenticated user.

    Returns:
        A :class:`ResponseEnvelope` containing the :class:`TradeRead` DTO.

    Raises:
        HTTPException: 404 if no trade with the given ID exists.
    """
    try:
        trade = await service.get_trade(trade_id)
    except TradeNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Trade not found.") from exc
    return ResponseEnvelope[TradeRead](data=trade)


@router.patch(
    "/{trade_id}",
    response_model=ResponseEnvelope[TradeRead],
    summary="Partially update a trade",
    description=(
        "Apply a partial update to an existing trade. Only fields present in "
        "the request body are modified; all other fields retain their current "
        "values. Suitable for closing an open trade by supplying `exit_price`, "
        "`closed_at`, and `pnl`."
    ),
    response_description=(
        "The trade after applying the partial update, wrapped in a response envelope."
    ),
    responses={
        200: {"description": "Trade updated successfully."},
        404: {"description": "Trade not found."},
        422: {"description": "Request payload failed validation."},
    },
)
async def update_trade(
    trade_id: uuid.UUID,
    payload: TradeUpdate,
    service: Annotated[TradeService, Depends(_get_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ResponseEnvelope[TradeRead]:
    """Apply a partial update to an existing trade.

    Only the fields present in the request body are modified.

    Args:
        trade_id: UUID path parameter identifying the trade.
        payload: Partial update data.
        service: Injected trade service.
        current_user: Injected authenticated user.

    Returns:
        A :class:`ResponseEnvelope` containing the updated
        :class:`TradeRead` DTO.

    Raises:
        HTTPException: 404 if no trade with the given ID exists.
    """
    try:
        trade = await service.update_trade(trade_id, payload)
    except TradeNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Trade not found.") from exc
    return ResponseEnvelope[TradeRead](data=trade)


@router.delete(
    "/{trade_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a trade",
    description=(
        "Permanently delete a trade record by its UUID. "
        "This operation is irreversible. Returns 204 No Content on success."
    ),
    responses={
        204: {"description": "Trade deleted successfully. No content returned."},
        404: {"description": "Trade not found."},
        422: {"description": "The supplied trade_id is not a valid UUID."},
    },
)
async def delete_trade(
    trade_id: uuid.UUID,
    service: Annotated[TradeService, Depends(_get_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Delete a trade by its UUID.

    Args:
        trade_id: UUID path parameter identifying the trade to remove.
        service: Injected trade service.
        current_user: Injected authenticated user.

    Raises:
        HTTPException: 404 if no trade with the given ID exists.
    """
    try:
        await service.delete_trade(trade_id)
    except TradeNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Trade not found.") from exc
