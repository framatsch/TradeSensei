"""Business-logic service for trade operations.

This layer orchestrates the repository and owns transaction semantics.
No HTTP concepts (``Request``, ``Response``, status codes) appear here.
"""

import logging
import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import SCREENSHOT_MAX_FILE_SIZE_MB
from app.core.exceptions import InvalidCursorError, TradeNotFoundError
from app.models.logical_execution import EXECUTION_ORIGIN_MANUAL
from app.models.trade import Trade
from app.repositories.account_repository import AccountRepository
from app.repositories.execution import ExecutionRepository
from app.repositories.playbook_repository import PlaybookRepository
from app.repositories.tag_repository import TagRepository
from app.repositories.trade_repository import TradeRepository
from app.schemas.common import CursorPage
from app.schemas.trade import (
    BulkTagMode,
    TradeCreate,
    TradeFilterParams,
    TradePartialCloseRequest,
    TradeRead,
    TradeSortParams,
    TradeUpdate,
)
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)


class TradeService:
    """Service layer for trade CRUD operations.

    Receives a session from the route handler and delegates all data
    access to repository classes.

    Args:
        session: An open :class:`AsyncSession` managed by the caller.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with a database session.

        Args:
            session: The session to use for all operations within this
                request.
        """
        self._session = session
        self._repo = TradeRepository(session)
        self._exec_repo = ExecutionRepository(session)
        self._tag_repo = TagRepository(session)
        self._playbook_repo = PlaybookRepository(session)
        self._account_repo = AccountRepository(session)
        self._cache = CacheService()

    def _screenshot_dir(self, trade_id: uuid.UUID) -> Path:
        """Return the filesystem directory used for trade screenshots."""
        base = Path(settings.upload_dir) / "screenshots" / str(trade_id)
        base.mkdir(parents=True, exist_ok=True)
        return base

    async def add_screenshot(
        self,
        trade_id: uuid.UUID,
        content: bytes,
        suffix: str,
        user_id: uuid.UUID,
    ) -> TradeRead:
        """Persist an uploaded screenshot and attach its URL to a trade.

        Args:
            trade_id: UUID of the trade to update.
            content: Raw file bytes of the screenshot.
            suffix: File extension suffix (e.g. ``".png"``).
            user_id: Authenticated user UUID for ownership checks.

        Returns:
            Updated trade DTO including the appended screenshot URL.

        Raises:
            TradeNotFoundError: If the target trade does not exist.
            ValueError: If the file exceeds the configured size limit.
        """
        max_size = SCREENSHOT_MAX_FILE_SIZE_MB * 1024 * 1024
        if len(content) > max_size:
            raise ValueError(
                f"File too large. Maximum size is {SCREENSHOT_MAX_FILE_SIZE_MB} MB."
            )

        safe_suffix = suffix if suffix.startswith(".") else f".{suffix}"
        filename = f"{uuid.uuid4()}{safe_suffix}"
        dest = self._screenshot_dir(trade_id) / filename
        dest.write_bytes(content)
        url = f"/uploads/screenshots/{trade_id}/{filename}"

        try:
            trade = await self.get_trade(trade_id, user_id)
            current_image_urls: list[str] = list(trade.image_urls or [])
            current_image_urls.append(url)
            return await self.update_trade(
                trade_id,
                TradeUpdate(image_urls=current_image_urls),
                user_id,
            )
        except TradeNotFoundError:
            dest.unlink(missing_ok=True)
            raise

    async def _re_aggregate_trade(self, trade_id: uuid.UUID) -> None:
        """Re-aggregate a trade from its logical executions.

        Delegates to :class:`ExecutionService._re_aggregate_trade` using the
        trade's owner for the permission check.

        Args:
            trade_id: UUID of the trade to re-aggregate.
        """
        # Deferred imports to break circular dependency: execution -> trade
        from sqlalchemy import select as _select  # noqa: PLC0415

        from app.services.execution import ExecutionService

        # Use a temporary lookup without user_id scoping (internal re-aggregate path).
        # This is safe because _re_aggregate_trade is only called from within service
        # methods that have already verified ownership upstream.
        _stmt = _select(Trade).where(Trade.id == trade_id)
        _result = await self._session.execute(_stmt)
        trade = _result.scalar_one_or_none()
        if not trade or trade.user_id is None:
            return

        exec_service = ExecutionService(self._session)
        await exec_service._re_aggregate_trade(trade_id, trade.user_id)

    async def create_trade(
        self,
        data: TradeCreate,
        portfolio_id: uuid.UUID | None = None,
    ) -> TradeRead:
        """Create a new trade record.

        Args:
            data: Validated creation payload.

        Returns:
            A :class:`TradeRead` DTO representing the created trade.
        """
        if data.account_id is not None and data.user_id is not None:
            account = await self._account_repo.get_by_id(
                data.account_id,
                data.user_id,
                portfolio_id,
            )
            if account is None:
                raise TradeNotFoundError(f"Account {data.account_id} not found.")

        trade: Trade = await self._repo.create(data)

        # Deferred import to break circular dependency: execution -> trade
        from app.models.logical_execution import EXECUTION_ORIGIN_MANUAL
        from app.models.trade import Direction as TradeDirection
        from app.repositories.execution import ExecutionRepository

        exec_repo = ExecutionRepository(self._session)

        # Determine the exit direction (opposite of trade direction).
        exit_direction = (
            TradeDirection.SHORT
            if trade.direction == TradeDirection.LONG
            else TradeDirection.LONG
        )

        if data.executions:
            # Bypass auto-generation and create manual execution legs
            for leg in data.executions:
                leg_asset_class = trade.asset_class
                leg_multiplier = trade.multiplier
                if trade.is_combo:
                    if leg.asset_class is not None:
                        leg_asset_class = leg.asset_class
                    if leg.multiplier is not None:
                        leg_multiplier = leg.multiplier
                else:
                    leg_asset_class = trade.asset_class
                    leg_multiplier = trade.multiplier
                if leg_asset_class is None:
                    raise ValueError(
                        "asset_class is required for execution legs on COMBO trades"
                    )
                await exec_repo.create(
                    user_id=trade.user_id,
                    account_id=trade.account_id,
                    symbol=trade.symbol,
                    asset_class=leg_asset_class,
                    direction=leg.direction,
                    quantity=leg.quantity,
                    price=leg.price,
                    commission=leg.commission,
                    executed_at=leg.executed_at,
                    multiplier=leg_multiplier,
                    currency=trade.currency,
                    origin=EXECUTION_ORIGIN_MANUAL,
                    trade_id=trade.id,
                    pnl=leg.pnl,
                )
        elif not trade.is_combo:
            # Always create a synthetic entry execution.
            await exec_repo.create(
                user_id=trade.user_id,
                account_id=trade.account_id,
                symbol=trade.symbol,
                asset_class=trade.asset_class,
                direction=trade.direction,
                quantity=trade.quantity,
                price=trade.entry_price,
                commission=trade.commission,
                executed_at=trade.opened_at,
                multiplier=trade.multiplier,
                currency=trade.currency,
                origin=EXECUTION_ORIGIN_MANUAL,
                trade_id=trade.id,
            )

            # If the trade is already closed (exit_price + closed_at provided),
            # also create a synthetic exit execution so the legs table is complete.
            is_closed = trade.closed_at is not None and trade.exit_price is not None
            if is_closed:
                await exec_repo.create(
                    user_id=trade.user_id,
                    account_id=trade.account_id,
                    symbol=trade.symbol,
                    asset_class=trade.asset_class,
                    direction=exit_direction,
                    quantity=trade.quantity,
                    price=trade.exit_price,
                    commission=trade.commission,
                    executed_at=trade.closed_at,
                    multiplier=trade.multiplier,
                    currency=trade.currency,
                    origin=EXECUTION_ORIGIN_MANUAL,
                    trade_id=trade.id,
                    pnl=trade.pnl,
                )

        # Re-aggregate only for open/manual-entry trades. Closed trades created via
        # API can include explicit exit/PnL values that cannot be reconstructed from
        # a single synthetic execution.
        should_reaggregate = bool(data.executions) or (
            not trade.is_combo
            and trade.closed_at is None
            and trade.exit_price is None
            and trade.pnl is None
            and trade.net_pnl is None
        )
        if should_reaggregate:
            await self._re_aggregate_trade(trade.id)

        if trade.user_id is None:
            raise TradeNotFoundError(f"Trade {trade.id} has no owner.")
        if trade.account_id is not None and trade.user_id is not None:
            account = await self._account_repo.get_by_id(
                trade.account_id,
                trade.user_id,
                portfolio_id,
            )
            if account is not None and account.portfolio_id is not None:
                await self._cache.invalidate_portfolio(
                    account.portfolio_id,
                    trade.user_id,
                )
        trade_reloaded = await self._repo.get_by_id(trade.id, trade.user_id)

        return TradeRead.model_validate(trade_reloaded)

    async def get_trade(
        self,
        trade_id: uuid.UUID,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID | None = None,
    ) -> TradeRead:
        """Fetch a single trade by its UUID.

        Args:
            trade_id: UUID of the trade to retrieve.
            user_id: Authenticated user UUID for ownership checks.

        Returns:
            A :class:`TradeRead` DTO for the requested trade.

        Raises:
            TradeNotFoundError: If no trade with the given ID exists.
        """
        trade = await self._repo.get_by_id(trade_id, user_id, portfolio_id)
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
        portfolio_id: uuid.UUID | None = None,
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
                portfolio_id=portfolio_id,
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
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID | None = None,
    ) -> TradeRead:
        """Partially update an existing trade.

        Args:
            trade_id: UUID of the trade to update.
            data: Validated partial update payload.
            user_id: Authenticated user UUID for ownership checks.

        Returns:
            A :class:`TradeRead` DTO reflecting the updated state.

        Raises:
            TradeNotFoundError: If no trade with the given ID exists.
        """
        trade = await self._repo.get_by_id(trade_id, user_id, portfolio_id)
        if trade is None:
            raise TradeNotFoundError(f"Trade {trade_id} not found.")
        pre_update_updated_at = trade.updated_at
        updated = await self._repo.update(trade, data)

        propagation_fields = {"playbook_id", "tag_ids", "notes", "user_rating"}
        should_propagate = bool(propagation_fields & data.model_fields_set)
        propagated_count = 0
        if should_propagate:
            propagated_count = (
                await self._repo.propagate_metadata_to_open_position_group(
                    source_trade=updated,
                    data=data,
                    user_id=user_id,
                    compare_updated_at=pre_update_updated_at,
                )
            )
            if propagated_count > 0:
                logger.info(
                    (
                        "trade_metadata.propagated user_id=%s trade_id=%s "
                        "position_id=%s fields=%s siblings=%d"
                    ),
                    user_id,
                    trade_id,
                    updated.position_id,
                    sorted(propagation_fields & data.model_fields_set),
                    propagated_count,
                )

        reaggregate_fields = {
            "direction",
            "multiplier",
        }
        should_reaggregate = bool(reaggregate_fields & data.model_fields_set)
        if should_reaggregate:
            await self._re_aggregate_trade(trade_id)
        if updated.account_id is not None:
            account = await self._account_repo.get_by_id(
                updated.account_id,
                user_id,
                portfolio_id,
            )
            if account is not None and account.portfolio_id is not None:
                await self._cache.invalidate_portfolio(account.portfolio_id, user_id)
        await self._session.commit()
        return TradeRead.model_validate(updated)

    async def delete_trade(
        self,
        trade_id: uuid.UUID,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID | None = None,
    ) -> None:
        """Delete a trade and its child executions.

        For each child :class:`~app.models.logical_execution.LogicalExecution`:
        - If ``origin`` is ``'manual'``, hard-delete (row removed).
        - Otherwise (``'imported'``, ``'merged'``, ``'split'``), soft-delete
          (``deleted=True``).

        The :class:`~app.models.trade.Trade` row itself is always hard-deleted.

        Args:
            trade_id: UUID of the trade to delete.
            user_id: Authenticated user UUID for ownership checks.

        Raises:
            TradeNotFoundError: If no trade with the given ID exists.
        """
        trade = await self._repo.get_by_id(trade_id, user_id, portfolio_id)
        if trade is None:
            raise TradeNotFoundError(f"Trade {trade_id} not found.")

        # Process child executions before deleting the parent trade
        executions = await self._exec_repo.list_by_trade_id(
            trade_id, include_deleted=True
        )
        for ex in executions:
            if ex.origin == EXECUTION_ORIGIN_MANUAL:
                await self._exec_repo.delete(ex.id)
            else:
                await self._exec_repo.soft_delete(ex.id)

        await self._repo.delete(trade)
        if trade.account_id is not None:
            account = await self._account_repo.get_by_id(
                trade.account_id,
                user_id,
                portfolio_id,
            )
            if account is not None and account.portfolio_id is not None:
                await self._cache.invalidate_portfolio(account.portfolio_id, user_id)

    async def bulk_delete_trades(
        self,
        trade_ids: list[uuid.UUID],
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID | None = None,
    ) -> int:
        """Bulk delete trades by their UUIDs.

        Only trades owned by ``user_id`` are deleted.

        Args:
            trade_ids: UUIDs of trades to delete.
            user_id: The authenticated user's UUID.

        Returns:
            Number of deleted trades.
        """
        deleted = await self._repo.bulk_delete(trade_ids, user_id, portfolio_id)
        if portfolio_id is not None:
            await self._cache.invalidate_portfolio(portfolio_id, user_id)
        return deleted

    async def bulk_assign_tags(
        self,
        trade_ids: list[uuid.UUID],
        tag_ids: list[uuid.UUID],
        mode: BulkTagMode,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID | None = None,
    ) -> int:
        """Bulk add or remove tags from trades.

        Validates that all tags belong to the requesting user before
        delegating to the repository.

        Args:
            trade_ids: UUIDs of trades to update.
            tag_ids: UUIDs of tags to add/remove.
            mode: ``BulkTagMode.add`` or ``BulkTagMode.remove``.
            user_id: The authenticated user's UUID.
        Returns:
            Number of trades updated.

        Raises:
            PermissionError: If any tag does not belong to ``user_id``.
        """
        tags = await self._tag_repo.get_many_by_ids(tag_ids, user_id)
        if len(tags) != len(tag_ids):
            raise ValueError("One or more tags not found.")
        if any(tag.user_id != user_id for tag in tags):
            raise PermissionError("One or more tags do not belong to this user.")
        updated = await self._repo.bulk_assign_tags(
            trade_ids,
            tag_ids,
            mode,
            user_id,
            portfolio_id,
        )
        if portfolio_id is not None:
            await self._cache.invalidate_portfolio(portfolio_id, user_id)
        return updated

    async def bulk_assign_playbook(
        self,
        trade_ids: list[uuid.UUID],
        playbook_id: uuid.UUID | None,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID | None = None,
    ) -> int:
        """Bulk assign or unassign a playbook on trades.

        Validates that the playbook belongs to the requesting user.

        Args:
            trade_ids: UUIDs of trades to update.
            playbook_id: UUID of playbook to assign, or ``None`` to unassign.
            user_id: The authenticated user's UUID.
        Returns:
            Number of trades updated.

        Raises:
            PermissionError: If the playbook does not belong to ``user_id``.
        """
        if playbook_id is not None:
            playbook = await self._playbook_repo.get_by_id(playbook_id, user_id)
            if playbook is None:
                raise ValueError("Playbook not found.")
            if playbook.user_id != user_id:
                raise PermissionError("Playbook does not belong to this user.")
        updated = await self._repo.bulk_assign_playbook(
            trade_ids,
            playbook_id,
            user_id,
            portfolio_id,
        )
        if portfolio_id is not None:
            await self._cache.invalidate_portfolio(portfolio_id, user_id)
        return updated

    async def merge_trades(
        self,
        trade_ids: list[uuid.UUID],
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID | None = None,
    ) -> TradeRead:
        """Merge multiple trades into a single trade.

        Args:
            trade_ids: The UUIDs of the trades to merge.
            user_id: The authenticated user's ID.

        Returns:
            The surviving TradeRead.

        Raises:
            TradeNotFoundError: If trades do not belong to the user.
            ValueError: If there is a mismatch in
                symbol/account/asset_class.
        """
        trades = []
        for tid in set(trade_ids):
            t = await self._repo.get_by_id(tid, user_id, portfolio_id)
            if not t:
                raise TradeNotFoundError(f"Trade {tid} not found or not owned.")
            trades.append(t)

        if len(trades) < 2:
            raise ValueError("Must provide at least two unique trades to merge.")

        ref_trade = trades[0]
        for t in trades[1:]:
            if (
                t.symbol != ref_trade.symbol
                or t.account_id != ref_trade.account_id
                or (
                    not t.is_combo
                    and not ref_trade.is_combo
                    and t.asset_class != ref_trade.asset_class
                )
            ):
                raise ValueError(
                    "Trades must have the same symbol, account, "
                    "and asset class to be merged."
                )

        # Sort trades by opened_at
        trades.sort(key=lambda t: t.opened_at)
        survivor = trades[0]
        non_survivors = trades[1:]

        # Deferred import to break circular dependency: execution -> trade
        from app.repositories.execution import ExecutionRepository

        exec_repo = ExecutionRepository(self._session)

        # Merge logic
        for t in non_survivors:
            # Reassign logical executions
            executions = await exec_repo.list_by_trade_id(t.id)
            execution_ids = [ex.id for ex in executions]
            await exec_repo.reassign_to_trade(execution_ids, survivor.id)

            # Append notes
            if t.notes:
                if survivor.notes:
                    survivor.notes += f"\n\n[Merged from {t.id}]:\n{t.notes}"
                else:
                    survivor.notes = t.notes

            # Move tags
            for tag in t.tags:
                if tag not in survivor.tags:
                    survivor.tags.append(tag)

            # Clear the ORM-level logical_executions collection before deleting
            # so that SQLAlchemy doesn't attempt to null-out the trade_id FK on
            # in-memory execution instances (they were already reassigned above).
            await self._session.refresh(t, attribute_names=["logical_executions"])

            # Delete empty trades
            await self._repo.delete(t)

        # Re-aggregate survivor
        await self._re_aggregate_trade(survivor.id)

        # Reload survivor
        survivor_reloaded = await self._repo.get_by_id(survivor.id, user_id)
        if portfolio_id is not None:
            await self._cache.invalidate_portfolio(portfolio_id, user_id)
        return TradeRead.model_validate(survivor_reloaded)

    async def partial_close_trade(
        self,
        trade_id: uuid.UUID,
        request: TradePartialCloseRequest,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID | None = None,
    ) -> TradeRead:
        """Partially close an open trade by splitting it into two records.

        If the closed quantity equals the total trade quantity, a standard
        full close is performed. Otherwise, the original trade is reduced
        and a new closed trade is created with a deep copy of all metadata.

        Args:
            trade_id: UUID of the open trade to split.
            request: Partial close details (quantity, price, timestamp).
            user_id: The authenticated user's UUID (for ownership verification).

        Returns:
            A :class:`TradeRead` DTO of the newly created closed trade.

        Raises:
            TradeNotFoundError: If the trade is not found or owned by another user.
            ValueError: If the trade is already closed or quantity is invalid.
        """
        trade = await self._repo.get_by_id(trade_id, user_id, portfolio_id)
        if trade is None:
            raise TradeNotFoundError(f"Trade {trade_id} not found.")

        if trade.closed_at is not None:
            raise ValueError("Cannot partially close a trade that is already closed.")

        if trade.quantity is None:
            raise ValueError("Cannot partially close a trade without quantity.")

        if request.quantity > trade.quantity:
            raise ValueError(
                f"Close quantity ({request.quantity}) exceeds "
                f"available quantity ({trade.quantity})."
            )

        # 1. Handle Full Close edge case.
        if request.quantity == trade.quantity:
            from app.models.trade import Direction
            from app.schemas.execution import LogicalExecutionCreate

            # Instead of updating TradeUpdate, we create an exit leg
            exit_direction = (
                Direction.SHORT if trade.direction == Direction.LONG else Direction.LONG
            )
            new_leg = LogicalExecutionCreate(
                direction=exit_direction,
                price=request.exit_price,
                quantity=request.quantity,
                commission=request.exit_commission,
                executed_at=request.closed_at,
            )
            # Add to trade.logical_executions
            # create the Execution object manually
            from app.models.logical_execution import LogicalExecution

            execution = LogicalExecution(
                trade_id=trade.id,
                user_id=trade.user_id,
                account_id=trade.account_id,
                symbol=trade.symbol,
                conid=trade.broker_conid,
                asset_class=trade.asset_class,
                multiplier=trade.multiplier,
                currency=trade.currency,
                direction=new_leg.direction,
                quantity=new_leg.quantity,
                price=new_leg.price,
                commission=new_leg.commission,
                executed_at=new_leg.executed_at,
                origin="manual",
                deleted=False,
                user_modified=False,
            )
            self._session.add(execution)
            await self._session.flush()

            # Reaggregate trade using the execution service logic
            await self._re_aggregate_trade(trade.id)
            if trade.account_id is not None:
                account = await self._account_repo.get_by_id(
                    trade.account_id,
                    user_id,
                    portfolio_id,
                )
                if account is not None and account.portfolio_id is not None:
                    await self._cache.invalidate_portfolio(
                        account.portfolio_id,
                        user_id,
                    )
            await self._session.commit()
            updated = await self._repo.get_by_id(trade.id, user_id)
            return TradeRead.model_validate(updated)

        # 2. Perform Split (Partial Close).
        # Refresh trade from DB to ensure all associations are correctly loaded
        # and current in the session before copying.
        await self._session.refresh(trade, attribute_names=["tags", "trade_notes"])
        tag_ids = [t.id for t in trade.tags]

        # Calculate proportional entry commission for the portion being closed.
        prop_entry_comm = (trade.commission * request.quantity) / trade.quantity

        # Update original trade: reduce quantity and subtract proportional commission.
        # We use setattr + flush directly since we have the ORM object.
        trade.quantity -= request.quantity
        trade.commission -= prop_entry_comm
        # Mark as manually edited to prevent broker re-import overrides if applicable.
        trade.is_manually_edited = True

        # Create new closed trade.
        new_trade_data = TradeCreate(
            user_id=user_id,
            position_id=trade.position_id,
            symbol=trade.symbol,
            direction=trade.direction,
            asset_class=trade.asset_class,
            quantity=request.quantity,
            entry_price=trade.entry_price,
            exit_price=request.exit_price,
            opened_at=trade.opened_at,
            closed_at=request.closed_at,
            commission=prop_entry_comm + request.exit_commission,
            account_id=trade.account_id,
            playbook_id=trade.playbook_id,
            tag_ids=tag_ids,
            notes=trade.notes,
            user_rating=trade.user_rating,
            currency=trade.currency,
            broker_conid=trade.broker_conid,
            is_manually_edited=True,
        )
        new_trade = await self._repo.create(new_trade_data)

        # Explicitly reload new_trade using the repository get_by_id method
        # which uses eager loading for everything.
        new_trade_orm = await self._repo.get_by_id(new_trade.id, user_id)
        if new_trade_orm is None:
            raise ValueError("Failed to retrieve created trade.")

        # Deep copy TradeNotes (psychological/review notes).
        # These are separate from the 'notes' column on the trade table.
        for note in trade.trade_notes:
            from app.models.trade_note import TradeNote

            self._session.add(
                TradeNote(
                    trade_id=new_trade_orm.id,
                    user_id=user_id,
                    content=note.content,
                    emotion=note.emotion,
                )
            )

        await self._session.flush()
        await self._session.refresh(new_trade_orm, attribute_names=["trade_notes"])

        if portfolio_id is not None:
            await self._cache.invalidate_portfolio(portfolio_id, user_id)

        return TradeRead.model_validate(new_trade_orm)
