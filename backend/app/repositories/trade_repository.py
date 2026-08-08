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

"""Async repository for the ``trades`` table.

All methods receive an :class:`AsyncSession` from the service layer and
return SQLAlchemy ORM instances.  No business logic lives here.
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast

from sqlalchemy import delete, exists, func, nullslast, or_, select
from sqlalchemy import update as sa_update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.selectable import Select

from app.core.constants import PAGINATION_DEFAULT_LIMIT, PAGINATION_MAX_LIMIT
from app.core.security import decode_cursor as _decode_signed_cursor
from app.core.security import encode_cursor as _encode_signed_cursor
from app.models.account import Account
from app.models.logical_execution import (
    EXECUTION_ORIGIN_IMPORTED,
    EXECUTION_ORIGIN_MANUAL,
    LogicalExecution,
)
from app.models.portfolio import Portfolio
from app.models.trade import Trade
from app.models.trade_annotation import TradeAnnotation
from app.models.trade_taxonomy import TradeTaxonomy
from app.schemas.trade import (
    BulkTaxonomyMode,
    TradeCreate,
    TradeFilterParams,
    TradeSortField,
    TradeSortParams,
    TradeUpdate,
)


def _get_cursor_secret() -> str:
    """Return the application secret for cursor signing.

    Uses a deferred import to avoid circular imports between
    ``security`` → ``config`` → ``database``.

    Returns:
        The ``SECRET_KEY`` from application settings.
    """
    # Deferred import to break circular dependency: security -> config
    from app.core.config import settings

    return str(settings.secret_key)


def _encode_cursor_payload(sort_value: str, trade_id: uuid.UUID) -> str:
    """Encode a sort-aware pagination cursor as an HMAC-signed token.

    Delegates to :func:`~app.core.security.encode_cursor` so the cursor
    is tamper-evident.  A manipulated cursor will fail signature verification
    before the SQL query runs.

    Args:
        sort_value: Serialised string representation of the sort field's
            value for the last item on the page.
        trade_id: The ``id`` of the last item on the page.

    Returns:
        An HMAC-signed, base64url-encoded cursor string.
    """
    payload = {"sv": sort_value, "id": str(trade_id)}
    return _encode_signed_cursor(payload, _get_cursor_secret())


def _decode_cursor_payload(cursor: str) -> tuple[str, uuid.UUID]:
    """Decode a sort-aware pagination cursor produced by :func:`_encode_cursor_payload`.

    Verifies the HMAC signature before returning the payload.

    Args:
        cursor: HMAC-signed, base64url-encoded cursor string.

    Returns:
        A tuple of ``(sort_val, trade_id)`` where ``sort_val`` is the
        raw string representation of the sort field value.

    Raises:
        ValueError: If the cursor cannot be decoded, has an invalid format,
            or the signature does not match.
    """
    payload = _decode_signed_cursor(cursor, _get_cursor_secret())
    sort_val = str(payload.get("sv", ""))
    trade_id = uuid.UUID(str(payload["id"]))
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
        return trade.asset_class.value if trade.asset_class is not None else ""
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

    expr = col.asc() if sort_dir == "asc" else col.desc()

    if sort_by in nullable_fields:
        return cast(ColumnElement[object], nullslast(expr))
    return cast(ColumnElement[object], expr)


def _trade_query_with_eager_loads() -> Select[tuple[Trade]]:
    """Return a base SELECT for Trade with eager-loaded relationships.

    Returns:
        A :func:`select` statement with ``selectinload`` options applied
        for the ``trade_notes``, ``playbook``, ``account``, and
        ``logical_executions`` relationships.
    """
    return select(Trade).options(
        selectinload(Trade.trade_notes),
        selectinload(Trade.playbook),
        selectinload(Trade.account),
        selectinload(Trade.logical_executions),
        selectinload(Trade.taxonomy_assignments).selectinload(TradeTaxonomy.taxonomy),
        selectinload(Trade.annotation_assignments).selectinload(TradeAnnotation.annotation_definition),
    )


def _apply_filters(
    stmt: Select[Any],
    filters: TradeFilterParams,
) -> Select[Any]:
    """Apply all active filter predicates to a SELECT statement.

    Filters are combined with AND logic at the top level. The taxonomy
    filter supports both AND mode (trade must have **all** listed
    taxonomies) and OR mode (trade must have **at least one** listed
    taxonomy).

    Compatible with any ``SELECT`` that queries the ``Trade`` table, including
    both full-row selects and scalar-column selects (e.g. ``Trade.id``).

    Args:
        stmt: The base SELECT statement to augment.
        filters: The filter parameters provided by the caller.

    Returns:
        The augmented SELECT statement with WHERE clauses applied.
    """
    if filters.symbols:
        symbol_conditions = []
        for sym in filters.symbols:
            escaped_sym = sym.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            symbol_conditions.append(Trade.symbol.ilike(f"{escaped_sym}%", escape="\\"))
        stmt = stmt.where(or_(*symbol_conditions))

    if filters.excluded_symbols:
        for sym in filters.excluded_symbols:
            escaped_sym = sym.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            stmt = stmt.where(Trade.symbol.not_ilike(f"{escaped_sym}%", escape="\\"))

    if filters.direction is not None:
        stmt = stmt.where(Trade.direction == filters.direction)

    if filters.is_combo is not None:
        stmt = stmt.where(Trade.is_combo == filters.is_combo)

    if filters.asset_classes is not None and len(filters.asset_classes) > 0:
        stmt = stmt.where(Trade.asset_class.in_(filters.asset_classes))

    if filters.taxonomy_ids:
        if filters.taxonomy_filter_mode == "and":
            taxonomy_subq = (
                select(TradeTaxonomy.trade_id)
                .where(TradeTaxonomy.taxonomy_id.in_(filters.taxonomy_ids))
                .group_by(TradeTaxonomy.trade_id)
                .having(func.count(func.distinct(TradeTaxonomy.taxonomy_id)) == len(filters.taxonomy_ids))
                .scalar_subquery()
            )
        else:  # "or"
            taxonomy_subq = select(TradeTaxonomy.trade_id).where(TradeTaxonomy.taxonomy_id.in_(filters.taxonomy_ids)).scalar_subquery()
        stmt = stmt.where(Trade.id.in_(taxonomy_subq))

    if filters.playbook_id is not None:
        stmt = stmt.where(Trade.playbook_id == filters.playbook_id)

    if filters.position_id is not None:
        stmt = stmt.where(Trade.position_id == filters.position_id)

    if filters.opened_at_from is not None:
        stmt = stmt.where(Trade.opened_at >= filters.opened_at_from)

    if filters.opened_at_to is not None:
        stmt = stmt.where(Trade.opened_at <= filters.opened_at_to)

    if filters.closed_at_from is not None:
        stmt = stmt.where(Trade.closed_at >= filters.closed_at_from)

    if filters.closed_at_to is not None:
        stmt = stmt.where(Trade.closed_at <= filters.closed_at_to)

    if filters.pnl_positive is True:
        stmt = stmt.where(Trade.pnl > Decimal("0"))
    elif filters.pnl_positive is False:
        stmt = stmt.where((Trade.pnl <= Decimal("0")) | (Trade.pnl.is_(None)))

    if filters.status == "open":
        stmt = stmt.where(Trade.closed_at.is_(None))
    elif filters.status == "closed":
        stmt = stmt.where(Trade.closed_at.is_not(None))

    if filters.account_id is not None:
        stmt = stmt.where(Trade.account_id == filters.account_id)

    if filters.hour_of_day is not None:
        stmt = stmt.where(func.extract("hour", Trade.opened_at) == filters.hour_of_day)

    if filters.day_of_week is not None:
        # PostgreSQL EXTRACT(DOW) returns 0=Sunday, 1=Monday, …, 6=Saturday.
        # Our API convention is 0=Monday, …, 6=Sunday (ISO).
        # Convert: postgres_dow = (api_day_of_week + 1) % 7
        stmt = stmt.where(func.extract("dow", Trade.opened_at) == (filters.day_of_week + 1) % 7)

    if filters.execution_state:
        execution_state_predicates: list[ColumnElement[bool]] = []
        for state in filters.execution_state:
            if state == "manual":
                execution_state_predicates.append(
                    exists(
                        select(LogicalExecution.id).where(
                            LogicalExecution.trade_id == Trade.id,
                            LogicalExecution.deleted.is_(False),
                            LogicalExecution.origin == EXECUTION_ORIGIN_MANUAL,
                        )
                    )
                )
            elif state == "edited":
                execution_state_predicates.append(
                    exists(
                        select(LogicalExecution.id).where(
                            LogicalExecution.trade_id == Trade.id,
                            LogicalExecution.deleted.is_(False),
                            LogicalExecution.user_modified.is_(True),
                        )
                    )
                )
            elif state == "imported":
                execution_state_predicates.append(
                    exists(
                        select(LogicalExecution.id).where(
                            LogicalExecution.trade_id == Trade.id,
                            LogicalExecution.deleted.is_(False),
                            LogicalExecution.origin == EXECUTION_ORIGIN_IMPORTED,
                            LogicalExecution.user_modified.is_(False),
                        )
                    )
                )
        if execution_state_predicates:
            stmt = stmt.where(or_(*execution_state_predicates))

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

    @property
    def session(self) -> AsyncSession:
        """Expose the active database session for service-level orchestration."""
        return self._session

    async def _set_taxonomies(self, trade: Trade, taxonomy_ids: list[uuid.UUID]) -> None:
        """Replace the taxonomy associations for a trade.

        Deletes existing ``trade_taxonomies`` rows for the trade and
        inserts new ones for the provided ``taxonomy_ids``.

        Args:
            trade: The trade ORM instance whose tags to replace.
            taxonomy_ids: New list of taxonomy UUIDs to associate.
        """
        await self._session.execute(delete(TradeTaxonomy).where(TradeTaxonomy.trade_id == trade.id))
        for taxonomy_id in taxonomy_ids:
            self._session.add(TradeTaxonomy(trade_id=trade.id, taxonomy_id=taxonomy_id))
        await self._session.flush()

    async def create(self, data: TradeCreate) -> Trade:
        """Persist a new trade and return the flushed ORM instance.

        The session is *flushed* (so the database assigns server
        defaults) but not committed — the service layer is responsible
        for committing.

        If ``data.taxonomy_ids`` is non-empty the association rows are
        inserted into ``trade_taxonomies`` after the trade is flushed.

        Args:
            data: Validated trade creation payload.

        Returns:
            The newly created :class:`Trade` with all server defaults
            populated (including eager-loaded taxonomy and
            ``trade_notes``).
        """
        create_dict = data.model_dump(exclude={"taxonomy_ids", "executions"})
        if create_dict.get("position_id") is None:
            create_dict.pop("position_id", None)
        trade = Trade(**create_dict)
        self._session.add(trade)
        await self._session.flush()

        if data.taxonomy_ids:
            await self._set_taxonomies(trade, data.taxonomy_ids)

        await self._session.refresh(
            trade,
            attribute_names=["taxonomy_assignments", "trade_notes", "playbook", "account"],
        )
        return trade

    async def bulk_create(self, trades: Sequence[TradeCreate]) -> int:
        """Persist multiple trades in one batch.

        Args:
            trades: Trade payloads to insert.

        Returns:
            Number of inserted rows.
        """
        if not trades:
            return 0

        for trade_data in trades:
            create_dict = trade_data.model_dump(exclude={"taxonomy_ids", "executions"})
            if create_dict.get("position_id") is None:
                create_dict.pop("position_id", None)
            self._session.add(Trade(**create_dict))

        await self._session.flush()
        return len(trades)

    async def find_by_broker_order_ids(
        self,
        user_id: uuid.UUID,
        broker_order_ids: Sequence[str],
    ) -> set[str]:
        """Return existing broker order IDs for a user.

        Args:
            user_id: Owning user UUID.
            broker_order_ids: Candidate broker order IDs.

        Returns:
            Set of existing broker order IDs for that user.
        """
        if not broker_order_ids:
            return set()

        stmt = select(Trade.broker_order_id).where(
            Trade.user_id == user_id,
            Trade.broker_order_id.in_(broker_order_ids),
        )
        result = await self._session.execute(stmt)
        return {row[0] for row in result if row[0] is not None}

    async def find_duplicate(
        self,
        user_id: uuid.UUID,
        symbol: str,
        opened_at: datetime,
        portfolio_id: uuid.UUID | None = None,
    ) -> bool:
        """Check whether a trade with the same key already exists.

        Args:
            user_id: Owning user UUID.
            symbol: Trade symbol.
            opened_at: Trade open timestamp.

        Returns:
            ``True`` when a matching row exists, otherwise ``False``.
        """
        stmt = select(Trade.id).where(
            Trade.user_id == user_id,
            Trade.symbol == symbol,
            Trade.opened_at == opened_at,
        )
        if portfolio_id is not None:
            stmt = (
                stmt.join(Account, Trade.account_id == Account.id)
                .join(Portfolio, Account.portfolio_id == Portfolio.id)
                .where(
                    Account.portfolio_id == portfolio_id,
                    Portfolio.user_id == user_id,
                )
            )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_by_id(
        self,
        trade_id: uuid.UUID,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID | None = None,
    ) -> Trade | None:
        """Retrieve a single trade by its primary key, scoped to a user.

        Eagerly loads ``trade_notes``, ``playbook``, ``account``,
        and ``logical_executions`` relationships.

        Args:
            trade_id: UUID of the trade to fetch.
            user_id: UUID of the requesting user — enforces ownership.

        Returns:
            The matching :class:`Trade`, or ``None`` if not found or not
            owned by the given user.
        """
        stmt = _trade_query_with_eager_loads().where(
            Trade.id == trade_id,
            Trade.user_id == user_id,
        )
        if portfolio_id is not None:
            stmt = (
                stmt.outerjoin(Account, Trade.account_id == Account.id)
                .outerjoin(Portfolio, Account.portfolio_id == Portfolio.id)
                .where(
                    or_(
                        Trade.account_id.is_(None),
                        Account.portfolio_id == portfolio_id,
                    )
                )
            )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_cursor(
        self,
        limit: int = PAGINATION_DEFAULT_LIMIT,
        cursor: str | None = None,
        include_total: bool = False,
        account_ids: list[uuid.UUID] | None = None,
        portfolio_id: uuid.UUID | None = None,
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

        Eagerly loads ``trade_notes`` on every row.

        Args:
            limit: Maximum number of items to return. Clamped to
                ``[1, PAGINATION_MAX_LIMIT]``.
            cursor: Opaque pagination cursor from a previous response.
            include_total: When ``True``, run an additional ``COUNT(*)``
                query and include the result in the return value.
                Defaults to ``False`` to avoid the extra query cost.
            account_ids: When provided, filter results to only trades
                belonging to the specified account UUIDs.
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
        effective_sort_by = sort.sort_by if sort is not None else TradeSortField.opened_at
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
        if account_ids:
            stmt = stmt.where(Trade.account_id.in_(account_ids))
        if portfolio_id is not None and user_id is not None:
            stmt = (
                stmt.join(Account, Trade.account_id == Account.id)
                .join(Portfolio, Account.portfolio_id == Portfolio.id)
                .where(
                    Account.portfolio_id == portfolio_id,
                    Portfolio.user_id == user_id,
                )
            )

        # ── Domain filters ───────────────────────────────────────────────────
        if filters is not None:
            stmt = _apply_filters(stmt, filters)
            if filters.annotation_filters and user_id is not None:
                from app.models.trade_annotation import TradeAnnotation as _TA
                from app.repositories._annotation_filter import apply_annotation_filters as _apply_af

                stmt = _apply_af(stmt, _TA, _TA.trade_id, Trade.id, user_id, filters.annotation_filters)

        # ── Cursor keyset condition ───────────────────────────────────────────
        if cursor is not None:
            sort_val_str, cursor_id = _decode_cursor_payload(cursor)

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
                if effective_sort_by == TradeSortField.opened_at or effective_sort_by == TradeSortField.closed_at:
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
                    stmt = stmt.where((sort_col < parsed_cursor_val) | ((sort_col == parsed_cursor_val) & (Trade.id < cursor_id)))
                else:  # asc
                    stmt = stmt.where((sort_col > parsed_cursor_val) | ((sort_col == parsed_cursor_val) & (Trade.id > cursor_id)))

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
            next_cursor = _encode_cursor_payload(sort_val, last.id)

        # ── Optional total count ──────────────────────────────────────────────
        total: int | None = None
        if include_total:
            # Build a filtered subquery from the same Trade base and wrap it
            # in COUNT(*) — this reuses _apply_filters directly instead of
            # duplicating its logic in a separate function.
            base_count = select(Trade.id)
            if user_id is not None:
                base_count = base_count.where(Trade.user_id == user_id)
            if account_ids:
                base_count = base_count.where(Trade.account_id.in_(account_ids))
            if portfolio_id is not None and user_id is not None:
                base_count = (
                    base_count.join(Account, Trade.account_id == Account.id)
                    .join(Portfolio, Account.portfolio_id == Portfolio.id)
                    .where(
                        Account.portfolio_id == portfolio_id,
                        Portfolio.user_id == user_id,
                    )
                )
            if filters is not None:
                base_count = _apply_filters(base_count, filters)
                if filters.annotation_filters and user_id is not None:
                    from app.models.trade_annotation import TradeAnnotation as _TA
                    from app.repositories._annotation_filter import apply_annotation_filters as _apply_af

                    base_count = _apply_af(base_count, _TA, _TA.trade_id, Trade.id, user_id, filters.annotation_filters)
            count_stmt = select(func.count()).select_from(base_count.subquery())
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
        ``None``) are written.  When ``data.taxonomy_ids`` is provided
        the existing taxonomy associations are replaced with the new set.
        The session is flushed but not committed.

        Args:
            trade: The ORM instance to update (already loaded from DB).
            data: Validated partial update payload.

        Returns:
            The updated :class:`Trade` instance after flush (with
            eager-loaded taxonomy assignments and ``trade_notes``).
        """
        update_data = data.model_dump(exclude_unset=True, exclude={"taxonomy_ids"})
        for field, value in update_data.items():
            setattr(trade, field, value)

        self._session.add(trade)
        await self._session.flush()

        if data.taxonomy_ids is not None:
            await self._set_taxonomies(trade, data.taxonomy_ids)

        # Refresh scalar columns first (e.g. updated_at set by DB trigger)
        # then load relationships, preventing MissingGreenlet errors when
        # model_validate accesses expired attributes outside the async context.
        await self._session.refresh(trade)
        await self._session.refresh(
            trade,
            attribute_names=["taxonomy_assignments", "trade_notes", "playbook", "account"],
        )
        return trade

    async def mark_manually_edited(self, trade_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Mark a trade as manually edited to protect its metadata from broker sync."""
        from sqlalchemy import update as sa_update

        stmt = sa_update(Trade).where(Trade.id == trade_id, Trade.user_id == user_id).values(is_manually_edited=True)
        await self._session.execute(stmt)
        await self._session.flush()

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
        portfolio_id: uuid.UUID | None = None,
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
        if portfolio_id is not None:
            scoped_ids_stmt = (
                select(Trade.id)
                .join(Account, Trade.account_id == Account.id)
                .join(Portfolio, Account.portfolio_id == Portfolio.id)
                .where(
                    Trade.id.in_(trade_ids),
                    Trade.user_id == user_id,
                    Account.portfolio_id == portfolio_id,
                    Portfolio.user_id == user_id,
                )
            )
            scoped_ids_result = await self._session.execute(scoped_ids_stmt)
            scoped_ids = list(scoped_ids_result.scalars().all())
            if not scoped_ids:
                return 0
            stmt = delete(Trade).where(Trade.id.in_(scoped_ids)).returning(Trade.id)
        else:
            stmt = delete(Trade).where(Trade.id.in_(trade_ids)).where(Trade.user_id == user_id).returning(Trade.id)
        result = await self._session.execute(stmt)
        deleted = list(result.scalars().all())
        await self._session.flush()
        return len(deleted)

    async def delete_by_user_account(
        self,
        user_id: uuid.UUID,
        account_id: uuid.UUID,
        include_manually_edited: bool = False,
        exclude_trade_ids: Sequence[uuid.UUID] | None = None,
    ) -> int:
        """Delete all trades for a user/account pair.

        Execution-overwrite-protection: when ``include_manually_edited`` is
        False, trades whose only remaining (non-deleted) execution legs are
        all ``user_modified=True`` are also preserved — independent of
        ``Trade.is_manually_edited``.

        Args:
            user_id: UUID of the owning user.
            account_id: UUID of the account to clear.
            include_manually_edited: When ``False``, preserves manually edited
                rows and trades backed solely by ``user_modified=True`` legs.
                When ``True``, deletes them too.
            exclude_trade_ids: Optional trade IDs to keep (e.g. still-open
                combo positions being carried forward across imports). All
                other trades for the account are deleted as usual.

        Returns:
            Number of deleted rows.
        """
        stmt = delete(Trade).where(
            Trade.user_id == user_id,
            Trade.account_id == account_id,
        )
        if not include_manually_edited:
            stmt = stmt.where(Trade.is_manually_edited.is_(False))

            # Protect trades whose every surviving leg is user-modified:
            # skip when at least one non-deleted leg exists AND no non-deleted
            # leg with user_modified=false exists.
            has_any_leg = exists(
                select(LogicalExecution.id).where(
                    LogicalExecution.trade_id == Trade.id,
                    LogicalExecution.deleted.is_(False),
                )
            )
            has_unprotected_leg = exists(
                select(LogicalExecution.id).where(
                    LogicalExecution.trade_id == Trade.id,
                    LogicalExecution.deleted.is_(False),
                    LogicalExecution.user_modified.is_(False),
                )
            )
            stmt = stmt.where(~(has_any_leg & ~has_unprotected_leg))
        if exclude_trade_ids:
            stmt = stmt.where(Trade.id.notin_(exclude_trade_ids))

        stmt = stmt.returning(Trade.id)  # type: ignore[assignment]
        result = await self._session.execute(stmt)
        deleted = list(result.scalars().all())
        await self._session.flush()
        return len(deleted)

    async def bulk_assign_taxonomies(
        self,
        trade_ids: list[uuid.UUID],
        taxonomy_ids: list[uuid.UUID],
        mode: BulkTaxonomyMode,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID | None = None,
    ) -> int:
        """Add or remove taxonomies on multiple trades.

        Only operates on trades belonging to ``user_id``. Other
        ``trade_ids`` are silently skipped.

        Args:
            trade_ids: Trade UUIDs to update.
            taxonomy_ids: Taxonomy UUIDs to add or remove.
            mode: ``BulkTaxonomyMode.add`` inserts rows (ON CONFLICT DO NOTHING),
                ``BulkTaxonomyMode.remove`` deletes matching rows.
            user_id: UUID of the owning user for ownership check.

        Returns:
            Number of trades actually updated.
        """
        # Verify ownership — get only trade IDs belonging to this user.
        owned_stmt = select(Trade.id).where(
            Trade.id.in_(trade_ids),
            Trade.user_id == user_id,
        )
        if portfolio_id is not None:
            owned_stmt = (
                owned_stmt.join(Account, Trade.account_id == Account.id)
                .join(Portfolio, Account.portfolio_id == Portfolio.id)
                .where(
                    Account.portfolio_id == portfolio_id,
                    Portfolio.user_id == user_id,
                )
            )
        owned_result = await self._session.execute(owned_stmt)
        owned_ids = list(owned_result.scalars().all())

        if not owned_ids:
            return 0

        if mode == BulkTaxonomyMode.add:
            for trade_id in owned_ids:
                for taxonomy_id in taxonomy_ids:
                    ins_stmt = pg_insert(TradeTaxonomy).values(trade_id=trade_id, taxonomy_id=taxonomy_id).on_conflict_do_nothing()
                    await self._session.execute(ins_stmt)
        else:  # BulkTaxonomyMode.remove
            await self._session.execute(
                delete(TradeTaxonomy).where(
                    TradeTaxonomy.trade_id.in_(owned_ids),
                    TradeTaxonomy.taxonomy_id.in_(taxonomy_ids),
                )
            )

        await self._session.flush()
        return len(owned_ids)

    async def bulk_assign_playbook(
        self,
        trade_ids: list[uuid.UUID],
        playbook_id: uuid.UUID | None,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID | None = None,
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
        if portfolio_id is not None:
            scoped_ids_stmt = (
                select(Trade.id)
                .join(Account, Trade.account_id == Account.id)
                .join(Portfolio, Account.portfolio_id == Portfolio.id)
                .where(
                    Trade.id.in_(trade_ids),
                    Trade.user_id == user_id,
                    Account.portfolio_id == portfolio_id,
                    Portfolio.user_id == user_id,
                )
            )
            scoped_ids_result = await self._session.execute(scoped_ids_stmt)
            scoped_ids = list(scoped_ids_result.scalars().all())
            if not scoped_ids:
                return 0
            stmt = sa_update(Trade).where(Trade.id.in_(scoped_ids)).values(playbook_id=playbook_id, is_manually_edited=True).returning(Trade.id)
        else:
            stmt = (
                sa_update(Trade)
                .where(Trade.id.in_(trade_ids), Trade.user_id == user_id)
                .values(playbook_id=playbook_id, is_manually_edited=True)
                .returning(Trade.id)
            )
        result = await self._session.execute(stmt)
        updated = list(result.scalars().all())
        await self._session.flush()
        return len(updated)

    async def list_open_by_position(
        self,
        user_id: uuid.UUID,
        position_id: uuid.UUID,
    ) -> list[Trade]:
        """Return open trades for a user-position group.

        Args:
            user_id: UUID of the owning user.
            position_id: Shared business position UUID.

        Returns:
            Open trades in that position group.
        """
        stmt = _trade_query_with_eager_loads().where(
            Trade.user_id == user_id,
            Trade.position_id == position_id,
            Trade.closed_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_position_id(
        self,
        trade_ids: Sequence[uuid.UUID],
        position_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> int:
        """Assign a shared position_id to a set of trades.

        Args:
            trade_ids: Target trade IDs.
            position_id: Position UUID to assign.
            user_id: UUID of the owning user.

        Returns:
            Number of rows updated.
        """
        if not trade_ids:
            return 0
        stmt = sa_update(Trade).where(Trade.id.in_(trade_ids), Trade.user_id == user_id).values(position_id=position_id).returning(Trade.id)
        result = await self._session.execute(stmt)
        updated = list(result.scalars().all())
        await self._session.flush()
        return len(updated)

    async def propagate_metadata_to_open_position_group(
        self,
        *,
        source_trade: Trade,
        data: TradeUpdate,
        user_id: uuid.UUID,
        compare_updated_at: datetime | None = None,
    ) -> int:
        """Propagate selected metadata fields to open siblings in a position.

        Uses a last-write-wins strategy: siblings that were updated *after* the
        source trade (i.e. ``sibling.updated_at > source_trade.updated_at``) are
        not overwritten.  This provides deterministic conflict resolution — the
        most recently edited trade wins on a field-by-field basis.

        The guard is applied at the SQL level so the comparison is atomic and not
        subject to Python-level race conditions.

        Args:
            source_trade: Trade that was explicitly updated by the user.
            data: Update payload used on the source trade.
            user_id: UUID of the owning user.

        Returns:
            Number of sibling trades actually updated (may be less than total
            siblings when some siblings were updated more recently).
        """
        if source_trade.position_id is None:
            return 0

        # Build scalar column updates only for fields present in the payload.
        scalar_values: dict[str, Any] = {}
        if "playbook_id" in data.model_fields_set:
            scalar_values["playbook_id"] = data.playbook_id
        if "journal" in data.model_fields_set:
            scalar_values["journal"] = data.journal
        if "user_rating" in data.model_fields_set:
            scalar_values["user_rating"] = data.user_rating

        updated_count = 0

        # Use caller-provided timestamp as conflict baseline when available.
        # This allows services to compare siblings against the source trade's
        # pre-update timestamp (strictly preserving newer independent sibling
        # edits during subsequent source updates).
        compare_time = compare_updated_at or source_trade.updated_at

        if scalar_values:
            # Bulk UPDATE with last-write-wins guard: only touch siblings whose
            # updated_at is older than (or equal to) the source's updated_at.
            stmt = (
                sa_update(Trade)
                .where(
                    Trade.user_id == user_id,
                    Trade.position_id == source_trade.position_id,
                    Trade.id != source_trade.id,
                    Trade.closed_at.is_(None),
                    Trade.updated_at <= compare_time,
                )
                .values(**scalar_values)
                .execution_options(synchronize_session="fetch")
            )
            result = await self._session.execute(stmt)
            updated_count = int(getattr(result, "rowcount", 0))

        if "taxonomy_ids" in data.model_fields_set and data.taxonomy_ids is not None:
            # For taxonomy assignments we must respect the same
            # last-write-wins boundary. Fetch
            # siblings that would have been eligible (updated_at <= source).
            siblings = await self.list_open_by_position(user_id, source_trade.position_id)
            eligible = [s for s in siblings if s.id != source_trade.id and s.updated_at <= compare_time]
            for sibling in eligible:
                await self._set_taxonomies(sibling, data.taxonomy_ids)
            await self._session.flush()
            # If scalar_values was empty (only taxonomy changed), set count from eligible.
            if not scalar_values:
                updated_count = len(eligible)

        return updated_count

    async def list_existing_entry_keys(
        self,
        user_id: uuid.UUID,
        account_id: uuid.UUID | None,
        portfolio_id: uuid.UUID | None = None,
    ) -> set[tuple[str, datetime, Decimal, Decimal, str]]:
        """Return dedupe keys for regular trades.

        Used by the import service to deduplicate entire executions from prior imports.
        Orphaned trades (entry_price == 0.001) are excluded.
        """
        stmt = select(
            Trade.symbol,
            Trade.opened_at,
            Trade.entry_price,
            Trade.quantity,
            Trade.direction,
        ).where(
            Trade.user_id == user_id,
            Trade.account_id == account_id,
            Trade.entry_price != Decimal("0.001"),
        )
        if portfolio_id is not None:
            stmt = (
                stmt.join(Account, Trade.account_id == Account.id)
                .join(Portfolio, Account.portfolio_id == Portfolio.id)
                .where(
                    Account.portfolio_id == portfolio_id,
                    Portfolio.user_id == user_id,
                )
            )
        result = await self._session.execute(stmt)
        return {
            (
                row.symbol,
                row.opened_at,
                row.entry_price,
                row.quantity,
                row.direction.value,
            )
            for row in result
        }

    async def list_existing_close_keys(
        self,
        user_id: uuid.UUID,
        account_id: uuid.UUID | None,
        portfolio_id: uuid.UUID | None = None,
    ) -> set[tuple[str, datetime, Decimal, Decimal, str]]:
        """Return dedupe keys for closed trades.

        Used by the import service to deduplicate orphaned trades from prior imports.
        """
        stmt = select(
            Trade.symbol,
            Trade.closed_at,
            Trade.exit_price,
            Trade.quantity,
            Trade.direction,
        ).where(
            Trade.user_id == user_id,
            Trade.account_id == account_id,
            Trade.closed_at.is_not(None),
        )
        if portfolio_id is not None:
            stmt = (
                stmt.join(Account, Trade.account_id == Account.id)
                .join(Portfolio, Account.portfolio_id == Portfolio.id)
                .where(
                    Account.portfolio_id == portfolio_id,
                    Portfolio.user_id == user_id,
                )
            )
        result = await self._session.execute(stmt)
        return {
            (
                row.symbol,
                row.closed_at,
                row.exit_price,
                row.quantity,
                row.direction.value,
            )
            for row in result
            if row.closed_at is not None and row.exit_price is not None
        }

    async def list_by_user_account(
        self,
        user_id: uuid.UUID,
        account_id: uuid.UUID,
    ) -> Sequence[Trade]:
        """List all trades for a given user and account.

        Args:
            user_id: Owning user UUID.
            account_id: Account UUID.

        Returns:
            A sequence of Trade instances.
        """
        stmt = select(Trade).where(
            Trade.user_id == user_id,
            Trade.account_id == account_id,
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def list_open_lots_by_user(
        self,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID | None = None,
    ) -> list[Trade]:
        """Return all open (unclosed) trades owned by *user_id*.

        "Open" means ``closed_at IS NULL``.  The result is ordered by
        ``opened_at ASC`` so that the FIFO aggregator receives lots in
        chronological order.

        Args:
            user_id: UUID of the owning user.

        Returns:
            A list of :class:`Trade` ORM instances (no eager loads — only
            the scalar columns needed by the aggregator are used).
        """
        stmt = select(Trade).where(Trade.user_id == user_id, Trade.closed_at.is_(None)).order_by(Trade.opened_at.asc())
        if portfolio_id is not None:
            stmt = (
                stmt.join(Account, Trade.account_id == Account.id)
                .join(Portfolio, Account.portfolio_id == Portfolio.id)
                .where(
                    Account.portfolio_id == portfolio_id,
                    Portfolio.user_id == user_id,
                )
            )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_open_combo_positions_by_user(
        self,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID | None = None,
        account_id: uuid.UUID | None = None,
    ) -> list[Trade]:
        """Return open COMBO trades with non-deleted opening legs loaded.

        Open COMBO positions are ``is_combo = true`` trades with ``closed_at IS NULL``.
        Their logical executions are eager-loaded so callers can derive the
        contract set from opening legs (`open_close='O'`, `deleted=false`).
        """
        stmt = (
            _trade_query_with_eager_loads()
            .where(
                Trade.user_id == user_id,
                Trade.is_combo.is_(True),
                Trade.closed_at.is_(None),
            )
            .order_by(Trade.opened_at.asc())
        )

        if account_id is not None:
            stmt = stmt.where(Trade.account_id == account_id)

        if portfolio_id is not None:
            stmt = (
                stmt.join(Account, Trade.account_id == Account.id)
                .join(Portfolio, Account.portfolio_id == Portfolio.id)
                .where(
                    Account.portfolio_id == portfolio_id,
                    Portfolio.user_id == user_id,
                )
            )

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_orphaned_lots_by_user(
        self,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID | None = None,
    ) -> list[Trade]:
        """Return all orphaned trades owned by *user_id*.

        "Orphaned" means ``entry_price == 0.001`` and ``closed_at IS NOT NULL``.
        The result is ordered by ``opened_at ASC`` so that the FIFO aggregator
        receives lots in chronological order.

        Args:
            user_id: UUID of the owning user.

        Returns:
            A list of :class:`Trade` ORM instances.
        """
        stmt = (
            select(Trade)
            .where(
                Trade.user_id == user_id,
                Trade.entry_price == Decimal("0.001"),
                Trade.closed_at.is_not(None),
            )
            .order_by(Trade.opened_at.asc())
        )
        if portfolio_id is not None:
            stmt = (
                stmt.join(Account, Trade.account_id == Account.id)
                .join(Portfolio, Account.portfolio_id == Portfolio.id)
                .where(
                    Account.portfolio_id == portfolio_id,
                    Portfolio.user_id == user_id,
                )
            )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def close_open_lot(
        self,
        trade_id: uuid.UUID,
        user_id: uuid.UUID,
        exit_price: Decimal,
        closed_at: datetime,
        pnl: Decimal | None,
        pnl_eur: Decimal | None,
        net_pnl: Decimal | None,
        net_pnl_eur: Decimal | None,
        commission_add: Decimal,
        quantity: Decimal,
    ) -> None:
        """Close an existing open trade lot in-place by setting exit fields.

        Updates ``exit_price``, ``closed_at``, ``pnl``, ``pnl_eur``,
        ``commission`` (incremented by *commission_add*), and ``quantity``
        on the row identified by *trade_id*.  The session is flushed but
        not committed.

        Args:
            trade_id: UUID of the open trade to close.
            exit_price: The execution price at which the position was closed.
            closed_at: Timezone-aware UTC timestamp of the close.
            pnl: Realised P&L in account currency, or ``None`` if unknown.
            pnl_eur: Realised P&L in EUR, or ``None`` if unknown.
            commission_add: Additional commission to add to the existing value.
            quantity: Final quantity of the closed lot (may differ from the
                original when a partial fill was matched).
        """
        stmt = (
            sa_update(Trade)
            .where(Trade.id == trade_id, Trade.user_id == user_id)
            .values(
                exit_price=exit_price,
                closed_at=closed_at,
                pnl=pnl,
                pnl_eur=pnl_eur,
                net_pnl=net_pnl,
                net_pnl_eur=net_pnl_eur,
                commission=Trade.commission + commission_add,
                quantity=quantity,
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def fill_orphaned_lot(
        self,
        trade_id: uuid.UUID,
        user_id: uuid.UUID,
        entry_price: Decimal,
        opened_at: datetime,
        pnl: Decimal | None,
        pnl_eur: Decimal | None,
        net_pnl: Decimal | None,
        net_pnl_eur: Decimal | None,
        commission_add: Decimal,
        quantity: Decimal,
    ) -> None:
        """Fill an existing orphaned lot in-place by setting entry fields.

        Updates ``entry_price``, ``opened_at``, ``pnl``, ``pnl_eur``,
        ``commission`` (incremented by *commission_add*), and ``quantity``
        on the row identified by *trade_id*. The session is flushed but
        not committed.
        """
        stmt = (
            sa_update(Trade)
            .where(Trade.id == trade_id, Trade.user_id == user_id)
            .values(
                entry_price=entry_price,
                opened_at=opened_at,
                pnl=pnl,
                pnl_eur=pnl_eur,
                net_pnl=net_pnl,
                net_pnl_eur=net_pnl_eur,
                commission=Trade.commission + commission_add,
                quantity=quantity,
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def close_open_combo_trade(
        self,
        trade_id: uuid.UUID,
        user_id: uuid.UUID,
        closed_at: datetime,
        pnl: Decimal | None,
        pnl_eur: Decimal | None,
        net_pnl: Decimal | None,
        net_pnl_eur: Decimal | None,
        commission_total: Decimal,
    ) -> None:
        """Close an existing open COMBO trade in-place.

        Updates close-related rollup fields while preserving nullable COMBO header
        fields (entry/exit/quantity remain null).
        """
        stmt = (
            sa_update(Trade)
            .where(
                Trade.id == trade_id,
                Trade.user_id == user_id,
                Trade.is_combo.is_(True),
            )
            .values(
                closed_at=closed_at,
                pnl=pnl,
                pnl_eur=pnl_eur,
                net_pnl=net_pnl,
                net_pnl_eur=net_pnl_eur,
                commission=commission_total,
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def list_manually_edited_keys(
        self,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID | None = None,
    ) -> set[tuple[str | None, datetime]]:
        """Return a set of ``(broker_conid, opened_at)`` tuples for all manually
        edited trades owned by *user_id*.

        This set is used by :class:`~app.services.import_service.ImportService`
        to skip re-importing trades that the user has manually corrected.

        Args:
            user_id: UUID of the owning user.

        Returns:
            A :class:`set` of ``(broker_conid, opened_at)`` tuples where
            ``broker_conid`` may be ``None`` for trades without a broker
            contract identifier.
        """
        stmt = select(Trade.broker_conid, Trade.opened_at).where(
            Trade.user_id == user_id,
            Trade.is_manually_edited.is_(True),
        )
        if portfolio_id is not None:
            stmt = (
                stmt.join(Account, Trade.account_id == Account.id)
                .join(Portfolio, Account.portfolio_id == Portfolio.id)
                .where(
                    Account.portfolio_id == portfolio_id,
                    Portfolio.user_id == user_id,
                )
            )
        result = await self._session.execute(stmt)
        return {(row.broker_conid, row.opened_at) for row in result}
