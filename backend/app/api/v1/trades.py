"""Route handlers for the ``/api/v1/trades`` resource."""

import uuid
from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    PAGINATION_DEFAULT_LIMIT,
    PAGINATION_MAX_LIMIT,
    PAGINATION_MIN_LIMIT,
)
from app.core.database import get_session
from app.core.deps import get_current_user
from app.core.exceptions import InvalidCursorError, TradeNotFoundError
from app.models.playbook import Playbook as PlaybookModel
from app.models.tag import Tag as TagModel
from app.models.user import User
from app.schemas.common import CursorPage, ResponseEnvelope
from app.schemas.trade import (
    BulkAssignPlaybookRequest,
    BulkAssignTagsRequest,
    BulkDeleteRequest,
    BulkDeleteResponse,
    BulkUpdateResponse,
    TradeCreateRequest,
    TradeFilterParams,
    TradeRead,
    TradeSortParams,
    TradeUpdate,
)
from app.services.trade_service import TradeService

router = APIRouter(prefix="/trades", tags=["trades"])


def _raise_not_found() -> NoReturn:
    """Raise a 404 HTTPException for a missing trade.

    Used as a single call-site for the repeated ``TradeNotFoundError``
    catch block across GET / PATCH / DELETE trade endpoints.
    """
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Trade not found.",
    )


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
    "/bulk/delete",
    response_model=ResponseEnvelope[BulkDeleteResponse],
    summary="Bulk delete trades",
    description=(
        "Permanently delete up to 100 trades in one request. "
        "Only trades owned by the authenticated user are deleted; "
        "any unrecognised IDs are silently skipped."
    ),
    response_description="Number of trades actually deleted.",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Bulk delete completed."},
        422: {"description": "Request payload failed validation."},
    },
)
async def bulk_delete_trades(
    payload: BulkDeleteRequest,
    service: Annotated[TradeService, Depends(_get_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ResponseEnvelope[BulkDeleteResponse]:
    """Bulk delete trades by their UUIDs.

    Only trades owned by the current user are deleted.  Other IDs are
    silently skipped — this operation is idempotent per unknown IDs.

    Args:
        payload: Request body containing the list of trade UUIDs.
        service: Injected trade service.
        current_user: Injected authenticated user.

    Returns:
        A :class:`ResponseEnvelope` containing the count of deleted trades.
    """
    deleted_count = await service.bulk_delete_trades(
        trade_ids=payload.trade_ids,
        user_id=current_user.id,
    )
    return ResponseEnvelope[BulkDeleteResponse](
        data=BulkDeleteResponse(deleted_count=deleted_count)
    )


@router.post(
    "/bulk/assign-tags",
    response_model=ResponseEnvelope[BulkUpdateResponse],
    summary="Bulk assign or remove tags",
    description=(
        "Add or remove tags from up to 100 trades in one request. "
        "All specified tags must belong to the authenticated user. "
        "In 'add' mode duplicate associations are silently ignored. "
        "In 'remove' mode non-existing associations are silently skipped."
    ),
    response_description="Number of trades actually updated.",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Bulk tag operation completed."},
        403: {"description": "One or more tags do not belong to this user."},
        404: {"description": "One or more tag UUIDs not found."},
        422: {"description": "Request payload failed validation."},
    },
)
async def bulk_assign_tags(
    payload: BulkAssignTagsRequest,
    service: Annotated[TradeService, Depends(_get_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ResponseEnvelope[BulkUpdateResponse]:
    """Bulk add or remove tags from trades.

    All specified tag UUIDs must exist and belong to the current user.

    Args:
        payload: Request body with trade IDs, tag IDs, and mode.
        service: Injected trade service.
        current_user: Injected authenticated user.
        session: Injected database session for tag ownership lookup.

    Returns:
        A :class:`ResponseEnvelope` containing the count of updated trades.

    Raises:
        HTTPException: 404 if any tag UUID is not found.
        HTTPException: 403 if any tag does not belong to the current user.
    """
    # Verify all requested tags exist and load their owner UUIDs.
    tag_result = await session.execute(
        sa_select(TagModel.user_id).where(TagModel.id.in_(payload.tag_ids))
    )
    tag_user_ids = list(tag_result.scalars().all())
    if len(tag_user_ids) != len(payload.tag_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more tags not found.",
        )

    try:
        updated_count = await service.bulk_assign_tags(
            trade_ids=payload.trade_ids,
            tag_ids=payload.tag_ids,
            mode=payload.mode,
            user_id=current_user.id,
            tag_user_ids=tag_user_ids,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    return ResponseEnvelope[BulkUpdateResponse](
        data=BulkUpdateResponse(updated_count=updated_count)
    )


@router.post(
    "/bulk/assign-playbook",
    response_model=ResponseEnvelope[BulkUpdateResponse],
    summary="Bulk assign playbook to trades",
    description=(
        "Assign or unassign a playbook on up to 100 trades in one request. "
        "The playbook must belong to the authenticated user. "
        "Set ``playbook_id`` to null to remove the playbook association."
    ),
    response_description="Number of trades actually updated.",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Bulk playbook assignment completed."},
        403: {"description": "Playbook does not belong to this user."},
        404: {"description": "Playbook UUID not found."},
        422: {"description": "Request payload failed validation."},
    },
)
async def bulk_assign_playbook(
    payload: BulkAssignPlaybookRequest,
    service: Annotated[TradeService, Depends(_get_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ResponseEnvelope[BulkUpdateResponse]:
    """Bulk assign or unassign a playbook on trades.

    The playbook must belong to the current user.  When ``playbook_id``
    is ``None`` the playbook association is removed from all matching trades.

    Args:
        payload: Request body with trade IDs and optional playbook UUID.
        service: Injected trade service.
        current_user: Injected authenticated user.
        session: Injected database session for playbook ownership lookup.

    Returns:
        A :class:`ResponseEnvelope` containing the count of updated trades.

    Raises:
        HTTPException: 404 if the playbook UUID is not found.
        HTTPException: 403 if the playbook does not belong to the current user.
    """
    playbook_user_id: uuid.UUID | None = None
    if payload.playbook_id is not None:
        pb_result = await session.execute(
            sa_select(PlaybookModel.user_id).where(
                PlaybookModel.id == payload.playbook_id
            )
        )
        playbook_user_id = pb_result.scalar_one_or_none()
        if playbook_user_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Playbook not found.",
            )

    try:
        updated_count = await service.bulk_assign_playbook(
            trade_ids=payload.trade_ids,
            playbook_id=payload.playbook_id,
            user_id=current_user.id,
            playbook_user_id=playbook_user_id,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    return ResponseEnvelope[BulkUpdateResponse](
        data=BulkUpdateResponse(updated_count=updated_count)
    )


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
    payload: TradeCreateRequest,
    service: Annotated[TradeService, Depends(_get_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ResponseEnvelope[TradeRead]:
    """Create and persist a new trading position.

    Args:
        payload: Validated trade creation data (without user_id).
        service: Injected trade service.
        current_user: Injected authenticated user — provides the user_id.

    Returns:
        A :class:`ResponseEnvelope` containing the created
        :class:`TradeRead` DTO.

    Raises:
        HTTPException: 422 if the payload fails Pydantic validation.
    """
    trade_create = payload.to_trade_create(user_id=current_user.id)
    trade = await service.create_trade(trade_create)
    return ResponseEnvelope[TradeRead](data=trade)


@router.get(
    "",
    response_model=ResponseEnvelope[CursorPage[TradeRead]],
    summary="List trades (cursor-paginated)",
    description=(
        "Return a cursor-paginated list of trades. The default sort order is "
        "``opened_at`` descending. Use ``sort_by`` and ``sort_dir`` to change "
        "the sort field and direction. Use the filter query parameters to narrow "
        "results. Pass the ``next_cursor`` value from the previous response as "
        "the ``cursor`` query parameter to fetch the next page."
    ),
    response_description=(
        "A page of trades wrapped in a response envelope, including a "
        "``next_cursor`` token and optional total count."
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
    cursor: Annotated[
        str | None,
        Query(description="Opaque pagination cursor from a previous response"),
    ] = None,
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
    filters: TradeFilterParams = Depends(),
    sort: TradeSortParams = Depends(),
) -> ResponseEnvelope[CursorPage[TradeRead]]:
    """Return a cursor-paginated list of trades with optional filter and sort.

    Args:
        service: Injected trade service.
        current_user: Injected authenticated user.
        cursor: Optional opaque cursor token from a previous response.
        limit: Number of items to return (1–100, default 20).
        include_total: When ``True``, include the total row count.
        account_id: Optional UUID to filter trades by account.
        filters: Optional filter parameters injected via ``Depends()``.
        sort: Optional sort parameters injected via ``Depends()``.

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
            user_id=current_user.id,
            filters=filters,
            sort=sort,
        )
    except InvalidCursorError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
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
    except TradeNotFoundError:
        _raise_not_found()
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
    except TradeNotFoundError:
        _raise_not_found()
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
    except TradeNotFoundError:
        _raise_not_found()
