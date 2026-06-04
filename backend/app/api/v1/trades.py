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

"""Route handlers for the ``/api/v1/trades`` resource."""

import uuid
from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    PAGINATION_DEFAULT_LIMIT,
    PAGINATION_MAX_LIMIT,
    PAGINATION_MIN_LIMIT,
)
from app.core.dependencies import require_portfolio_owner
from app.core.deps import get_current_user, get_session_with_rls
from app.core.exceptions import (
    ConfigurationError,
    InvalidCursorError,
    TradeNotFoundError,
    UnsupportedContentTypeError,
)
from app.models.user import User
from app.schemas.common import CursorPage, ResponseEnvelope
from app.schemas.trade import (
    AssetClass,
    BulkAssignPlaybookRequest,
    BulkAssignTaxonomiesRequest,
    BulkDeleteRequest,
    BulkDeleteResponse,
    BulkUpdateResponse,
    MergeTradesRequest,
    TradeCreateRequest,
    TradeFilterParams,
    TradeImageUploadUrlRequest,
    TradeImageUploadUrlResponse,
    TradePartialCloseRequest,
    TradeRead,
    TradeSortParams,
    TradeUpdate,
)
from app.services.storage_service import StorageService
from app.services.trade_service import TradeService

router = APIRouter(
    prefix="/portfolios/{portfolio_id}/trades",
    tags=["trades"],
    dependencies=[Depends(require_portfolio_owner)],
)

global_router = APIRouter(
    prefix="/trades",
    tags=["trades"],
)


@global_router.post(
    "/upload-url",
    response_model=ResponseEnvelope[TradeImageUploadUrlResponse],
    summary="Get trade image upload URL",
    responses={
        200: {"description": "Presigned URL generated successfully."},
        422: {"description": "Validation error or unsupported content type."},
        503: {"description": "Object storage is not configured."},
    },
)
async def get_trade_image_upload_url(
    payload: TradeImageUploadUrlRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> ResponseEnvelope[TradeImageUploadUrlResponse]:
    """Generate a presigned PUT URL for uploading a trade image.

    The client must upload the file directly to the returned `presigned_url`
    using an HTTP PUT request with the exact `content_type`.

    Once uploaded, the `key` can be stored in the trade's `image_urls` list.
    """
    service = StorageService()
    try:
        presigned_url, key = service.generate_trade_image_upload_url(
            user_id=current_user.id,
            filename=payload.filename,
            content_type=payload.content_type,
        )
    except UnsupportedContentTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except ConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return ResponseEnvelope(
        data=TradeImageUploadUrlResponse(
            presigned_url=presigned_url,
            key=key,
        )
    )


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
    session: Annotated[AsyncSession, Depends(get_session_with_rls)],
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
    portfolio_id: uuid.UUID,
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
        portfolio_id=portfolio_id,
    )
    return ResponseEnvelope[BulkDeleteResponse](data=BulkDeleteResponse(deleted_count=deleted_count))


@router.post(
    "/bulk/assign-taxonomies",
    response_model=ResponseEnvelope[BulkUpdateResponse],
    summary="Bulk assign or remove taxonomies",
    description=(
        "Add or remove taxonomies from up to 100 trades in one request. "
        "All specified taxonomies must belong to the authenticated user. "
        "In 'add' mode duplicate associations are silently ignored. "
        "In 'remove' mode non-existing associations are silently skipped."
    ),
    response_description="Number of trades actually updated.",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Bulk taxonomy operation completed."},
        403: {"description": "One or more taxonomies do not belong to this user."},
        404: {"description": "One or more taxonomy UUIDs not found."},
        422: {"description": "Request payload failed validation."},
    },
)
async def bulk_assign_taxonomies(
    portfolio_id: uuid.UUID,
    payload: BulkAssignTaxonomiesRequest,
    service: Annotated[TradeService, Depends(_get_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ResponseEnvelope[BulkUpdateResponse]:
    """Bulk add or remove taxonomies from trades.

    All specified taxonomy UUIDs must exist and belong to the current user.

    Args:
        payload: Request body with trade IDs, taxonomy IDs, and mode.
        service: Injected trade service.
        current_user: Injected authenticated user.
    Returns:
        A :class:`ResponseEnvelope` containing the count of updated trades.

    Raises:
        HTTPException: 404 if any taxonomy UUID is not found.
        HTTPException: 403 if any taxonomy does not belong to the current user.
    """
    try:
        updated_count = await service.bulk_assign_taxonomies(
            trade_ids=payload.trade_ids,
            taxonomy_ids=payload.taxonomy_ids,
            mode=payload.mode,
            user_id=current_user.id,
            portfolio_id=portfolio_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    return ResponseEnvelope[BulkUpdateResponse](data=BulkUpdateResponse(updated_count=updated_count))


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
    portfolio_id: uuid.UUID,
    payload: BulkAssignPlaybookRequest,
    service: Annotated[TradeService, Depends(_get_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ResponseEnvelope[BulkUpdateResponse]:
    """Bulk assign or unassign a playbook on trades.

    The playbook must belong to the current user.  When ``playbook_id``
    is ``None`` the playbook association is removed from all matching trades.

    Args:
        payload: Request body with trade IDs and optional playbook UUID.
        service: Injected trade service.
        current_user: Injected authenticated user.
    Returns:
        A :class:`ResponseEnvelope` containing the count of updated trades.

    Raises:
        HTTPException: 404 if the playbook UUID is not found.
        HTTPException: 403 if the playbook does not belong to the current user.
    """
    try:
        updated_count = await service.bulk_assign_playbook(
            trade_ids=payload.trade_ids,
            playbook_id=payload.playbook_id,
            user_id=current_user.id,
            portfolio_id=portfolio_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    return ResponseEnvelope[BulkUpdateResponse](data=BulkUpdateResponse(updated_count=updated_count))


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
    portfolio_id: uuid.UUID,
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
    trade = await service.create_trade(trade_create, portfolio_id)
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
    response_description=("A page of trades wrapped in a response envelope, including a ``next_cursor`` token and optional total count."),
    responses={
        200: {"description": "Paginated list of trades."},
        400: {"description": "Cursor token is malformed or expired."},
        422: {"description": "Query parameter validation error."},
    },
)
async def list_trades(
    portfolio_id: uuid.UUID,
    service: Annotated[TradeService, Depends(_get_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    filters: Annotated[TradeFilterParams, Depends()],
    sort: Annotated[TradeSortParams, Depends()],
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
        Query(description=("When true, include the total row count across all pages. Adds a COUNT(*) query; omit for best performance.")),
    ] = False,
    account_id: Annotated[
        uuid.UUID | None,
        Query(description="Filter trades by account UUID"),
    ] = None,
    account_ids: Annotated[
        list[uuid.UUID] | None,
        Query(description="Filter trades by one or more account UUIDs"),
    ] = None,
    taxonomy_ids: Annotated[
        list[uuid.UUID] | None,
        Query(description=("Filter trades by taxonomy UUIDs (OR logic: returns trades with any of the given taxonomies)")),
    ] = None,
    symbols: Annotated[
        list[str] | None,
        Query(description="List of symbols to include."),
    ] = None,
    excluded_symbols: Annotated[
        list[str] | None,
        Query(description="List of symbols to exclude."),
    ] = None,
    asset_classes: Annotated[
        list[AssetClass] | None,
        Query(description="Filter by asset classes."),
    ] = None,
) -> ResponseEnvelope[CursorPage[TradeRead]]:
    """Return a cursor-paginated list of trades with optional filter and sort.

    Args:
        service: Injected trade service.
        current_user: Injected authenticated user.
        cursor: Optional opaque cursor token from a previous response.
        limit: Number of items to return (1–100, default 20).
        include_total: When ``True``, include the total row count.
        account_id: Optional UUID to filter trades by account.
        account_ids: Optional list of UUIDs to filter trades by one or more accounts.
        taxonomy_ids: Optional list of taxonomy UUIDs to filter by (OR logic).
        filters: Optional filter parameters injected via ``Depends()``.
        sort: Optional sort parameters injected via ``Depends()``.

    Returns:
        A :class:`ResponseEnvelope` wrapping a :class:`CursorPage` of
        :class:`TradeRead` DTOs.

    Raises:
        HTTPException: 400 if the cursor token is malformed.
    """
    # Inject taxonomy_ids from the explicit Query parameter into filters.
    # FastAPI cannot parse list query params from Pydantic Depends() models,
    # so taxonomy_ids is declared separately and merged here.
    if taxonomy_ids is not None:
        filters.taxonomy_ids = taxonomy_ids
    if symbols is not None:
        filters.symbols = symbols
    if excluded_symbols is not None:
        filters.excluded_symbols = excluded_symbols
    if asset_classes is not None:
        filters.asset_classes = asset_classes

    selected_account_ids = account_ids[:] if account_ids is not None else []
    if account_id is not None:
        selected_account_ids.append(account_id)
    filters.account_id = None
    try:
        page = await service.list_trades(
            limit=limit,
            cursor=cursor,
            include_total=include_total,
            account_ids=selected_account_ids or None,
            user_id=current_user.id,
            portfolio_id=portfolio_id,
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
    description=("Retrieve the full details of a single trade by its UUID. Returns 404 if no trade with the supplied ID exists."),
    response_description="The requested trade wrapped in a response envelope.",
    responses={
        200: {"description": "Trade found and returned."},
        404: {"description": "Trade not found."},
        422: {"description": "The supplied trade_id is not a valid UUID."},
    },
)
async def get_trade(
    portfolio_id: uuid.UUID,
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
        trade = await service.get_trade(trade_id, current_user.id, portfolio_id)
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
    response_description=("The trade after applying the partial update, wrapped in a response envelope."),
    responses={
        200: {"description": "Trade updated successfully."},
        404: {"description": "Trade not found."},
        422: {"description": "Request payload failed validation."},
    },
)
async def update_trade(
    portfolio_id: uuid.UUID,
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
        trade = await service.update_trade(
            trade_id,
            payload,
            current_user.id,
            portfolio_id,
        )
    except TradeNotFoundError:
        _raise_not_found()
    return ResponseEnvelope[TradeRead](data=trade)


@router.delete(
    "/{trade_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a trade",
    description=("Permanently delete a trade record by its UUID. This operation is irreversible. Returns 204 No Content on success."),
    responses={
        204: {"description": "Trade deleted successfully. No content returned."},
        404: {"description": "Trade not found."},
        422: {"description": "The supplied trade_id is not a valid UUID."},
    },
)
async def delete_trade(
    portfolio_id: uuid.UUID,
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
        await service.delete_trade(trade_id, current_user.id, portfolio_id)
    except TradeNotFoundError:
        _raise_not_found()


@router.post(
    "/{trade_id}/partial-close",
    response_model=ResponseEnvelope[TradeRead],
    summary="Partially close an open trade",
    description=(
        "Split an open trade into two records: "
        "the original trade with reduced quantity "
        "and a new closed trade with the specified "
        "exit details. All metadata (tags, "
        "notes, playbook) is duplicated to the "
        "new trade. Entry commissions are split "
        "proportionally."
    ),
    response_description=("The newly created closed trade wrapped in a response envelope."),
    responses={
        200: {"description": "Trade partially closed successfully."},
        400: {"description": "Invalid partial close request (e.g. quantity too high)."},
        404: {"description": "Trade not found."},
        422: {"description": "Request payload failed validation."},
    },
)
async def partial_close_trade(
    portfolio_id: uuid.UUID,
    trade_id: uuid.UUID,
    payload: TradePartialCloseRequest,
    service: Annotated[TradeService, Depends(_get_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ResponseEnvelope[TradeRead]:
    """Partially close an open trade by splitting it.

    Args:
        trade_id: UUID of the open trade to split.
        payload: Partial close details (quantity, price, timestamp).
        service: Injected trade service.
        current_user: Injected authenticated user.

    Returns:
        A :class:`ResponseEnvelope` containing the new closed trade.

    Raises:
        HTTPException: 404 if the trade is not found.
        HTTPException: 400 if the trade is already closed or quantity is invalid.
    """
    try:
        new_trade = await service.partial_close_trade(
            trade_id=trade_id,
            request=payload,
            user_id=current_user.id,
            portfolio_id=portfolio_id,
        )
        return ResponseEnvelope[TradeRead](data=new_trade)
    except TradeNotFoundError:
        _raise_not_found()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/merge",
    response_model=ResponseEnvelope[TradeRead],
    status_code=status.HTTP_200_OK,
    summary="Merge multiple trades",
    description=("Merge multiple trades of the same symbol and account into a single trade."),
)
async def merge_trades(
    portfolio_id: uuid.UUID,
    payload: MergeTradesRequest,
    service: Annotated[TradeService, Depends(_get_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ResponseEnvelope[TradeRead]:
    """Merge multiple trades into one."""
    try:
        survivor = await service.merge_trades(
            payload.trade_ids,
            current_user.id,
            portfolio_id,
        )
        return ResponseEnvelope[TradeRead](data=survivor)
    except TradeNotFoundError:
        _raise_not_found()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
