"""Async repository for the ``trades`` table.

All methods receive an :class:`AsyncSession` from the service layer and
return SQLAlchemy ORM instances.  No business logic lives here.
"""

import base64
import binascii
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import delete, func, nullslast, select
from sqlalchemy import update as sa_update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.selectable import Select

from app.core.constants import PAGINATION_DEFAULT_LIMIT, PAGINATION_MAX_LIMIT
from app.models.trade import Trade
from app.models.trade_tag import TradeTag
from app.schemas.trade import (
    BulkTagMode,
    TradeCreate,
    TradeFilterParams,
    TradeSortField,
    TradeSortParams,
    TradeUpdate,
)


def _encode_cursor(sort_value: str, trade_id: uuid.UUID) -> str:
    """Encode a sort-aware pagination cursor as a URL-safe base-64 string.

    The cursor encodes the current sort field value and the trade ``id``
    so the query can use a composite keyset condition, ensuring stable
    ordering even when multiple trades share the same sort value.

    Args:
        sort_value: Serialised string representation of the sort field's
            value for the last item on the page.
        trade_id: The ``id`` of the last item on the page.

    Returns:
        A URL-safe base-64 encoded cursor string.
    """
    raw = f"{sort_value}|{trade_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[str, uuid.UUID]:
    """Decode a sort-aware pagination cursor produced by :func:`_encode_cursor`.

    Args:
        cursor: URL-safe base-64 encoded cursor string.

    Returns:
        A tuple of ``(sort_val, trade_id)`` where ``sort_val`` is the
        raw string representation of the sort field value.

    Raises:
        ValueError: If the cursor cannot be decoded or has an invalid format.
    """
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        sort_val, id_part = raw.split("|", 1)
        trade_id = uuid.UUID(id_part)
    except (ValueError, binascii.Error) as exc:
        raise ValueError(f"Invalid pagination cursor: {cursor!r}") from exc
    return sort_val, trade_id


def _get_sort_value(trade: Trade, sort_by: TradeSortField) -> str:
    """Serialise the sort field value of a Trade instance to a string.

    Used when encoding the pagination cursor for the last item on a page.
    Nullable fields that are ``None`` are encoded as an empty string.

    Args:
        trade: The :class:`Trade` ORM instance.
        sort_by: The active sort field.

    Returns:
        String representation of the sort field value.
    """
    if sort_by == TradeSortField.opened_at:
        opened_at = trade.opened_at
        if opened_at.tzinfo is None:
            opened_at = opened_at.replace(tzinfo=UTC)
        return opened_at.isoformat()
    if sort_by == TradeSortField.closed_at:
        return trade.closed_at.isoformat() if trade.closed_at is not None else ""
    if sort_by == TradeSortField.pnl:
        return str(trade.pnl) if trade.pnl is not None else ""
    if sort_by == TradeSortField.exit_price:
        return str(trade.exit_price) if trade.exit_price is not None else ""
    if sort_by == TradeSortField.symbol:
        return trade.symbol
    if sort_by == TradeSortField.direction:
        return trade.direction.value
    if sort_by == TradeSortField.asset_class:
        return trade.asset_class.value
    if sort_by == TradeSortField.entry_price:
        return str(trade.entry_price)
    if sort_by == TradeSortField.quantity:
        return str(trade.quantity)
    # Fallback — should never be reached given the exhaustive enum above.
    return ""  # pragma: no cover


def _build_sort_column(
    sort_by: TradeSortField,
    sort_dir: str,
) -> ColumnElement[object]:
    """Map a :class:`TradeSortField` to a SQLAlchemy order-by expression.

    Nullable columns (``pnl``, ``exit_price``, ``closed_at``) use
    ``NULLS LAST`` so that rows with ``NULL`` values always appear after
    non-null rows regardless of sort direction.

    Args:
        sort_by: The field to sort by.
        sort_dir: ``"asc"`` or ``"desc"``.

    Returns:
        A SQLAlchemy column expression suitable for use in
        :meth:`~sqlalchemy.sql.selectable.Select.order_by`.
    """
    nullable_fields = {
        TradeSortField.pnl,
        TradeSortField.exit_price,
        TradeSortField.closed_at,
    }

    column_map = {
        TradeSortField.symbol: Trade.symbol,
        TradeSortField.direction: Trade.direction,
        TradeSortField.asset_class: Trade.asset_class,
        TradeSortField.entry_price: Trade.entry_price,
        TradeSortField.exit_price: Trade.exit_price,
        TradeSortField.pnl: Trade.pnl,
        TradeSortField.quantity: Trade.quantity,
        TradeSortField.opened_at: Trade.opened_at,
        TradeSortField.closed_at: Trade.closed_at,
    }
    col = column_map[sort_by]

    if sort_dir == "asc":
        expr = col.asc()
    else:
        expr = col.desc()

    if sort_by in nullable_fields:
        return nullslast(expr)
    return expr


def _trade_query_with_eager_loads() -> Select[tuple[Trade]]:
    """Return a base SELECT for Trade with tags and notes eager-loaded.

    Returns:
        A :func:`select` statement with ``selectinload`` options applied
        for the ``tags`` and ``trade_notes`` relationships.
    """
    return select(Trade).options(
        selectinload(Trade.tags),
        selectinload(Trade.trade_notes),
    )


def _apply_filters(
    stmt: Select[tuple[Trade]],
    filters: TradeFilterParams,
) -> Select[tuple[Trade]]:
    """Apply all active filter predicates to a SELECT statement.

    Filters are combined with AND logic at the top level. The tag filter
    supports both AND mode (trade must have **all** listed tags) and OR
    mode (trade must have **at least one** listed tag).

    Args:
        stmt: The base SELECT statement to augment.
        filters: The filter parameters provided by the caller.

    Returns:
        The augmented SELECT statement with WHERE clauses applied.
    """
    if filters.symbol:
        stmt = stmt.where(Trade.symbol.ilike(f"%{filters.symbol}%"))

    if filters.direction is not None:
        stmt = stmt.where(Trade.direction == filters.direction)

    if filters.asset_class is not None:
        stmt = stmt.where(Trade.asset_class == filters.asset_class)

    if filters.tag_ids:
        if filters.tag_filter_mode == "and":
            tag_subq = (
                select(TradeTag.trade_id)
                .where(TradeTag.tag_id.in_(filters.tag_ids))
                .group_by(TradeTag.trade_id)
                .having(
                    func.count(func.distinct(TradeTag.tag_id)) == len(filters.tag_ids)
                )
                .scalar_subquery()
            )
        else:  # "or"
            tag_subq = (
                select(TradeTag.trade_id)
                .where(TradeTag.tag_id.in_(filters.tag_ids))
                .scalar_subquery()
            )
        stmt = stmt.where(Trade.id.in_(tag_subq))

    if filters.playbook_id is not None:
        stmt = stmt.where(Trade.playbook_id == filters.playbook_id)

    if filters.opened_at_from is not None:
        stmt = stmt.where(Trade.opened_at >= filters.opened_at_from)

    if filters.opened_at_to is not None:
        stmt = stmt.where(Trade.opened_at <= filters.opened_at_to)

    if filters.pnl_positive is True:
        stmt = stmt.where(Trade.pnl > Decimal("0"))
    elif filters.pnl_positive is False:
        stmt = stmt.where((Trade.pnl <= Decimal("0")) | (Trade.pnl.is_(None)))

    return stmt


class TradeRepository:
    """Data-access object for the ``trades`` table.

    Accepts an :class:`AsyncSession` at construction time so that the
    same database transaction can span multiple repository calls.

    Args:
        session: An open :class:`AsyncSession` managed by the caller.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the repository with an existing session.

        Args:
            session: The database session to use for all queries.
        """
        self._session = session

    async def _set_tags(self, trade: Trade, tag_ids: list[uuid.UUID]) -> None:
        """Replace the tag associations for a trade.

        Deletes existing ``trade_tags`` rows for the trade and inserts
        new ones for the provided ``tag_ids``.  The caller is responsible
        for ensuring all tag_ids belong to the same user as the trade.

        Args:
            trade: The trade ORM instance whose tags to replace.
            tag_ids: New list of tag UUIDs to associate.
        """
        await self._session.execute(
            delete(TradeTag).where(TradeTag.trade_id == trade.id)
        )
        for tag_id in tag_ids:
            self._session.add(TradeTag(trade_id=trade.id, tag_id=tag_id))
        await self._session.flush()

    async def create(self, data: TradeCreate) -> Trade:
        """Persist a new trade and return the flushed ORM instance.

        The session is *flushed* (so the database assigns server
        defaults) but not committed — the service layer is responsible
        for committing.

        If ``data.tag_ids`` is non-empty the association rows are
        inserted into ``trade_tags`` after the trade is flushed.

        Args:
            data: Validated trade creation payload.

        Returns:
            The newly created :class:`Trade` with all server defaults
            populated (including eager-loaded ``tags`` and
            ``trade_notes``).
        """
        create_dict = data.model_dump(exclude={"tag_ids"})
        trade = Trade(**create_dict)
        self._session.add(trade)
        await self._session.flush()

        if data.tag_ids:
            await self._set_tags(trade, data.tag_ids)

        await self._session.refresh(trade, attribute_names=["tags", "trade_notes"])
        return trade

    async def get_by_id(self, trade_id: uuid.UUID) -> Trade | None:
        """Retrieve a single trade by its primary key.

        Eagerly loads ``tags`` and ``trade_notes`` relationships.

        Args:
            trade_id: UUID of the trade to fetch.

        Returns:
            The matching :class:`Trade`, or ``None`` if not found.
        """
        stmt = _trade_query_with_eager_loads().where(Trade.id == trade_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_cursor(
        self,
        limit: int = PAGINATION_DEFAULT_LIMIT,
        cursor: str | None = None,
        include_total: bool = False,
        account_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        filters: TradeFilterParams | None = None,
        sort: TradeSortParams | None = None,
    ) -> tuple[list[Trade], str | None, int | None]:
        """Return a cursor-paginated page of trades with optional filter and sort.

        Trades are ordered by the chosen sort field (default ``opened_at DESC``)
        with ``id`` as a tie-breaker for stable pagination.  When a ``cursor``
        is supplied the query applies a composite keyset filter so only rows
        *after* the cursor position are returned.

        Filter predicates (when provided via ``filters``) are applied before
        the cursor condition.  The same filters are applied to the optional
        ``COUNT(*)`` query so that ``total`` reflects the filtered row count.

        Eagerly loads ``tags`` and ``trade_notes`` on every row.

        Args:
            limit: Maximum number of items to return. Clamped to
                ``[1, PAGINATION_MAX_LIMIT]``.
            cursor: Opaque pagination cursor from a previous response.
            include_total: When ``True``, run an additional ``COUNT(*)``
                query and include the result in the return value.
                Defaults to ``False`` to avoid the extra query cost.
            account_id: When provided, filter results to only trades
                belonging to the specified account UUID.
            user_id: When provided, filter results to only trades
                belonging to the specified user UUID.
            filters: Optional filter parameters to narrow the result set.
            sort: Optional sort parameters.  Defaults to
                ``(opened_at DESC, id DESC)``.

        Returns:
            A three-tuple of:

            - ``items``: list of :class:`Trade` instances (length ≤ ``limit``).
            - ``next_cursor``: encoded cursor for the next page, or ``None``
              if this is the last page.
            - ``total``: filtered total row count, or ``None`` when
              ``include_total`` is ``False``.

        Raises:
            ValueError: If the supplied cursor is malformed.
        """
        clamped_limit = max(1, min(limit, PAGINATION_MAX_LIMIT))

        # Resolve sort parameters (use defaults when not provided).
        effective_sort_by = (
            sort.sort_by if sort is not None else TradeSortField.opened_at
        )
        effective_sort_dir = sort.sort_dir if sort is not None else "desc"

        primary_order = _build_sort_column(effective_sort_by, effective_sort_dir)
        # Secondary tie-breaker on id mirrors the primary direction.
        id_order: ColumnElement[object] = (
            Trade.id.asc() if effective_sort_dir == "asc" else Trade.id.desc()  # type: ignore[assignment]
        )
        stmt = _trade_query_with_eager_loads().order_by(primary_order, id_order)

        # ── Ownership / account filters ──────────────────────────────────────
        if user_id is not None:
            stmt = stmt.where(Trade.user_id == user_id)
        if account_id is not None:
            stmt = stmt.where(Trade.account_id == account_id)

        # ── Domain filters ───────────────────────────────────────────────────
        if filters is not None:
            stmt = _apply_filters(stmt, filters)

        # ── Cursor keyset condition ───────────────────────────────────────────
        if cursor is not None:
            sort_val_str, cursor_id = _decode_cursor(cursor)

            # When sort_val is empty (NULL-valued sort field at cursor position),
            # skip the keyset condition — the client resets the cursor when
            # changing sort, so this edge-case only arises for NULL tails.
            if sort_val_str:
                sort_col = {
                    TradeSortField.symbol: Trade.symbol,
                    TradeSortField.direction: Trade.direction,
                    TradeSortField.asset_class: Trade.asset_class,
                    TradeSortField.entry_price: Trade.entry_price,
                    TradeSortField.exit_price: Trade.exit_price,
                    TradeSortField.pnl: Trade.pnl,
                    TradeSortField.quantity: Trade.quantity,
                    TradeSortField.opened_at: Trade.opened_at,
                    TradeSortField.closed_at: Trade.closed_at,
                }[effective_sort_by]

                # Parse the cursor value to the correct Python type for comparison.
                parsed_cursor_val: object
                if (
                    effective_sort_by == TradeSortField.opened_at
                    or effective_sort_by == TradeSortField.closed_at
                ):
                    parsed_cursor_val = datetime.fromisoformat(sort_val_str)
                elif effective_sort_by in (
                    TradeSortField.entry_price,
                    TradeSortField.exit_price,
                    TradeSortField.pnl,
                    TradeSortField.quantity,
                ):
                    parsed_cursor_val = Decimal(sort_val_str)
                else:
                    # symbol, direction, asset_class — string comparison
                    parsed_cursor_val = sort_val_str

                if effective_sort_dir == "desc":
                    stmt = stmt.where(
                        (sort_col < parsed_cursor_val)
                        | ((sort_col == parsed_cursor_val) & (Trade.id < cursor_id))
                    )
                else:  # asc
                    stmt = stmt.where(
                        (sort_col > parsed_cursor_val)
                        | ((sort_col == parsed_cursor_val) & (Trade.id > cursor_id))
                    )

        # ── Fetch page + one probe row ────────────────────────────────────────
        stmt = stmt.limit(clamped_limit + 1)
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())

        has_more = len(rows) > clamped_limit
        items = rows[:clamped_limit]

        next_cursor: str | None = None
        if has_more and items:
            last = items[-1]
            sort_val = _get_sort_value(last, effective_sort_by)
            next_cursor = _encode_cursor(sort_val, last.id)

        # ── Optional total count ──────────────────────────────────────────────
        total: int | None = None
        if include_total:
            count_stmt = select(func.count()).select_from(Trade)
            if user_id is not None:
                count_stmt = count_stmt.where(Trade.user_id == user_id)
            if account_id is not None:
                count_stmt = count_stmt.where(Trade.account_id == account_id)
            if filters is not None:
                # Re-apply filters to the count query via the base Trade select.
                # We build a subquery approach: apply filter conditions directly.
                count_stmt = _apply_filters_to_count(count_stmt, filters)
            count_result = await self._session.execute(count_stmt)
            total = count_result.scalar_one_or_none()

        return items, next_cursor, total

    async def update(
        self,
        trade: Trade,
        data: TradeUpdate,
    ) -> Trade:
        """Apply a partial update to an existing trade.

        Only fields that are explicitly set in *data* (i.e. not
        ``None``) are written.  When ``data.tag_ids`` is provided the
        existing tag associations are replaced with the new set.
        The session is flushed but not committed.

        Args:
            trade: The ORM instance to update (already loaded from DB).
            data: Validated partial update payload.

        Returns:
            The updated :class:`Trade` instance after flush (with
            eager-loaded ``tags`` and ``trade_notes``).
        """
        update_data = data.model_dump(exclude_unset=True, exclude={"tag_ids"})
        for field, value in update_data.items():
            setattr(trade, field, value)
        self._session.add(trade)
        await self._session.flush()

        if data.tag_ids is not None:
            await self._set_tags(trade, data.tag_ids)

        await self._session.refresh(trade, attribute_names=["tags", "trade_notes"])
        return trade

    async def delete(self, trade: Trade) -> None:
        """Delete a trade from the database.

        The session is flushed but not committed — the service layer
        commits the transaction.

        Args:
            trade: The ORM instance to delete.
        """
        await self._session.delete(trade)
        await self._session.flush()

    async def bulk_delete(
        self,
        trade_ids: list[uuid.UUID],
        user_id: uuid.UUID,
    ) -> int:
        """Delete multiple trades belonging to the given user.

        Only trades that exist AND belong to ``user_id`` are deleted.
        Other IDs are silently skipped.

        Args:
            trade_ids: List of trade UUIDs to delete.
            user_id: UUID of the owning user.

        Returns:
            Number of trades actually deleted.
        """
        stmt = (
            delete(Trade)
            .where(Trade.id.in_(trade_ids))
            .where(Trade.user_id == user_id)
            .returning(Trade.id)
        )
        result = await self._session.execute(stmt)
        deleted = list(result.scalars().all())
        await self._session.flush()
        return len(deleted)

    async def bulk_assign_tags(
        self,
        trade_ids: list[uuid.UUID],
        tag_ids: list[uuid.UUID],
        mode: BulkTagMode,
        user_id: uuid.UUID,
    ) -> int:
        """Add or remove tags on multiple trades.

        Only operates on trades belonging to ``user_id``. Other
        ``trade_ids`` are silently skipped.

        Args:
            trade_ids: Trade UUIDs to update.
            tag_ids: Tag UUIDs to add or remove.
            mode: ``BulkTagMode.add`` inserts rows (ON CONFLICT DO NOTHING),
                ``BulkTagMode.remove`` deletes matching rows.
            user_id: UUID of the owning user for ownership check.

        Returns:
            Number of trades actually updated.
        """
        # Verify ownership — get only trade IDs belonging to this user.
        owned_stmt = select(Trade.id).where(
            Trade.id.in_(trade_ids),
            Trade.user_id == user_id,
        )
        owned_result = await self._session.execute(owned_stmt)
        owned_ids = list(owned_result.scalars().all())

        if not owned_ids:
            return 0

        if mode == BulkTagMode.add:
            for trade_id in owned_ids:
                for tag_id in tag_ids:
                    ins_stmt = (
                        pg_insert(TradeTag)
                        .values(trade_id=trade_id, tag_id=tag_id)
                        .on_conflict_do_nothing()
                    )
                    await self._session.execute(ins_stmt)
        else:  # BulkTagMode.remove
            await self._session.execute(
                delete(TradeTag).where(
                    TradeTag.trade_id.in_(owned_ids),
                    TradeTag.tag_id.in_(tag_ids),
                )
            )

        await self._session.flush()
        return len(owned_ids)

    async def bulk_assign_playbook(
        self,
        trade_ids: list[uuid.UUID],
        playbook_id: uuid.UUID | None,
        user_id: uuid.UUID,
    ) -> int:
        """Assign or unassign a playbook on multiple trades.

        Only operates on trades belonging to ``user_id``.

        Args:
            trade_ids: Trade UUIDs to update.
            playbook_id: Playbook UUID to assign, or ``None`` to unassign.
            user_id: UUID of the owning user.

        Returns:
            Number of trades actually updated.
        """
        stmt = (
            sa_update(Trade)
            .where(Trade.id.in_(trade_ids), Trade.user_id == user_id)
            .values(playbook_id=playbook_id)
            .returning(Trade.id)
        )
        result = await self._session.execute(stmt)
        updated = list(result.scalars().all())
        await self._session.flush()
        return len(updated)


def _apply_filters_to_count(
    count_stmt: Select[tuple[int]],
    filters: TradeFilterParams,
) -> Select[tuple[int]]:
    """Apply filter predicates to a ``COUNT(*)`` SELECT statement.

    Mirrors the logic in :func:`_apply_filters` but operates on the
    count query which selects from the ``Trade`` table directly.

    Args:
        count_stmt: The ``COUNT(*)`` SELECT to augment.
        filters: The filter parameters provided by the caller.

    Returns:
        The augmented count SELECT statement.
    """
    if filters.symbol:
        count_stmt = count_stmt.where(Trade.symbol.ilike(f"%{filters.symbol}%"))

    if filters.direction is not None:
        count_stmt = count_stmt.where(Trade.direction == filters.direction)

    if filters.asset_class is not None:
        count_stmt = count_stmt.where(Trade.asset_class == filters.asset_class)

    if filters.tag_ids:
        if filters.tag_filter_mode == "and":
            tag_subq = (
                select(TradeTag.trade_id)
                .where(TradeTag.tag_id.in_(filters.tag_ids))
                .group_by(TradeTag.trade_id)
                .having(
                    func.count(func.distinct(TradeTag.tag_id)) == len(filters.tag_ids)
                )
                .scalar_subquery()
            )
        else:  # "or"
            tag_subq = (
                select(TradeTag.trade_id)
                .where(TradeTag.tag_id.in_(filters.tag_ids))
                .scalar_subquery()
            )
        count_stmt = count_stmt.where(Trade.id.in_(tag_subq))

    if filters.playbook_id is not None:
        count_stmt = count_stmt.where(Trade.playbook_id == filters.playbook_id)

    if filters.opened_at_from is not None:
        count_stmt = count_stmt.where(Trade.opened_at >= filters.opened_at_from)

    if filters.opened_at_to is not None:
        count_stmt = count_stmt.where(Trade.opened_at <= filters.opened_at_to)

    if filters.pnl_positive is True:
        count_stmt = count_stmt.where(Trade.pnl > Decimal("0"))
    elif filters.pnl_positive is False:
        count_stmt = count_stmt.where(
            (Trade.pnl <= Decimal("0")) | (Trade.pnl.is_(None))
        )

    return count_stmt
