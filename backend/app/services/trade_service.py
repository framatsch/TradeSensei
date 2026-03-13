"""Business-logic service for trade operations.

This layer orchestrates the repository and owns transaction semantics.
No HTTP concepts (``Request``, ``Response``, status codes) appear here.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidCursorError, TradeNotFoundError
from app.models.trade import Trade
from app.repositories.trade_repository import TradeRepository
from app.schemas.common import CursorPage
from app.schemas.trade import (
    BulkTagMode,
    TradeCreate,
    TradeFilterParams,
    TradeRead,
    TradeSortParams,
    TradeUpdate,
)


class TradeService:
    """Service layer for trade CRUD operations.

    Receives a session from the route handler and delegates all data
    access to :class:`~app.repositories.trade_repository.TradeRepository`.

    Args:
        session: An open :class:`AsyncSession` managed by the caller.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with a database session.

        Args:
            session: The session to use for all operations within this
                request.
        """
        self._repo = TradeRepository(session)

    async def create_trade(self, data: TradeCreate) -> TradeRead:
        """Create a new trade record.

        Args:
            data: Validated creation payload.

        Returns:
            A :class:`TradeRead` DTO representing the created trade.
        """
        trade: Trade = await self._repo.create(data)
        return TradeRead.model_validate(trade)

    async def get_trade(self, trade_id: uuid.UUID) -> TradeRead:
        """Fetch a single trade by its UUID.

        Args:
            trade_id: UUID of the trade to retrieve.

        Returns:
            A :class:`TradeRead` DTO for the requested trade.

        Raises:
            TradeNotFoundError: If no trade with the given ID exists.
        """
        trade = await self._repo.get_by_id(trade_id)
        if trade is None:
            raise TradeNotFoundError(f"Trade {trade_id} not found.")
        return TradeRead.model_validate(trade)

    async def list_trades(
        self,
        limit: int,
        cursor: str | None,
        include_total: bool = False,
        account_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        filters: TradeFilterParams | None = None,
        sort: TradeSortParams | None = None,
    ) -> CursorPage[TradeRead]:
        """Return a cursor-paginated list of trades.

        Args:
            limit: Maximum number of trades to return per page.
            cursor: Opaque pagination cursor from a previous response.
            include_total: When ``True``, include the total row count in
                the response. Defaults to ``False`` to skip the extra
                ``COUNT(*)`` query.
            account_id: When provided, only trades for this account are
                returned.
            user_id: When provided, only trades belonging to this user
                are returned.
            filters: Optional filter parameters to narrow the result set.
            sort: Optional sort parameters. Defaults to
                ``(opened_at DESC, id DESC)``.

        Returns:
            A :class:`CursorPage` containing the trade DTOs, a
            ``next_cursor`` token, and an optional total count.

        Raises:
            InvalidCursorError: If the cursor token is malformed.
        """
        try:
            items, next_cursor, total = await self._repo.list_cursor(
                limit=limit,
                cursor=cursor,
                include_total=include_total,
                account_id=account_id,
                user_id=user_id,
                filters=filters,
                sort=sort,
            )
        except ValueError as exc:
            raise InvalidCursorError("Invalid pagination cursor.") from exc

        return CursorPage[TradeRead](
            items=[TradeRead.model_validate(t) for t in items],
            next_cursor=next_cursor,
            total=total,
        )

    async def update_trade(
        self,
        trade_id: uuid.UUID,
        data: TradeUpdate,
    ) -> TradeRead:
        """Partially update an existing trade.

        Args:
            trade_id: UUID of the trade to update.
            data: Validated partial update payload.

        Returns:
            A :class:`TradeRead` DTO reflecting the updated state.

        Raises:
            TradeNotFoundError: If no trade with the given ID exists.
        """
        trade = await self._repo.get_by_id(trade_id)
        if trade is None:
            raise TradeNotFoundError(f"Trade {trade_id} not found.")
        updated = await self._repo.update(trade, data)
        return TradeRead.model_validate(updated)

    async def delete_trade(self, trade_id: uuid.UUID) -> None:
        """Delete a trade by its UUID.

        Args:
            trade_id: UUID of the trade to delete.

        Raises:
            TradeNotFoundError: If no trade with the given ID exists.
        """
        trade = await self._repo.get_by_id(trade_id)
        if trade is None:
            raise TradeNotFoundError(f"Trade {trade_id} not found.")
        await self._repo.delete(trade)

    async def bulk_delete_trades(
        self,
        trade_ids: list[uuid.UUID],
        user_id: uuid.UUID,
    ) -> int:
        """Bulk delete trades by their UUIDs.

        Only trades owned by ``user_id`` are deleted.

        Args:
            trade_ids: UUIDs of trades to delete.
            user_id: The authenticated user's UUID.

        Returns:
            Number of deleted trades.
        """
        return await self._repo.bulk_delete(trade_ids, user_id)

    async def bulk_assign_tags(
        self,
        trade_ids: list[uuid.UUID],
        tag_ids: list[uuid.UUID],
        mode: BulkTagMode,
        user_id: uuid.UUID,
        tag_user_ids: list[uuid.UUID],
    ) -> int:
        """Bulk add or remove tags from trades.

        Validates that all tags belong to the requesting user before
        delegating to the repository.

        Args:
            trade_ids: UUIDs of trades to update.
            tag_ids: UUIDs of tags to add/remove.
            mode: ``BulkTagMode.add`` or ``BulkTagMode.remove``.
            user_id: The authenticated user's UUID.
            tag_user_ids: ``user_id`` values of the provided tags,
                fetched by the route handler for ownership validation.

        Returns:
            Number of trades updated.

        Raises:
            PermissionError: If any tag does not belong to ``user_id``.
        """
        if any(uid != user_id for uid in tag_user_ids):
            raise PermissionError("One or more tags do not belong to this user.")
        return await self._repo.bulk_assign_tags(trade_ids, tag_ids, mode, user_id)

    async def bulk_assign_playbook(
        self,
        trade_ids: list[uuid.UUID],
        playbook_id: uuid.UUID | None,
        user_id: uuid.UUID,
        playbook_user_id: uuid.UUID | None,
    ) -> int:
        """Bulk assign or unassign a playbook on trades.

        Validates that the playbook belongs to the requesting user.

        Args:
            trade_ids: UUIDs of trades to update.
            playbook_id: UUID of playbook to assign, or ``None`` to unassign.
            user_id: The authenticated user's UUID.
            playbook_user_id: ``user_id`` of the playbook (``None`` if
                unassigning), fetched by the route handler.

        Returns:
            Number of trades updated.

        Raises:
            PermissionError: If the playbook does not belong to ``user_id``.
        """
        if playbook_id is not None and playbook_user_id != user_id:
            raise PermissionError("Playbook does not belong to this user.")
        return await self._repo.bulk_assign_playbook(trade_ids, playbook_id, user_id)
