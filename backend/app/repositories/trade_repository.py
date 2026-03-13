"""Async repository for the ``trades`` table.

All methods receive an :class:`AsyncSession` from the service layer and
return SQLAlchemy ORM instances.  No business logic lives here.
"""

import base64
import binascii
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import PAGINATION_DEFAULT_LIMIT, PAGINATION_MAX_LIMIT
from app.models.trade import Trade
from app.schemas.trade import TradeCreate, TradeUpdate


def _encode_cursor(opened_at: datetime, trade_id: uuid.UUID) -> str:
    """Encode a pagination cursor as a URL-safe base-64 string.

    The cursor encodes both ``opened_at`` and ``id`` so the query can
    use a composite keyset condition, ensuring stable ordering even
    when multiple trades share the same timestamp.

    Args:
        opened_at: The ``opened_at`` value of the last item on the page.
        trade_id: The ``id`` of the last item on the page.

    Returns:
        A URL-safe base-64 encoded cursor string.
    """
    raw = f"{opened_at.isoformat()}|{trade_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    """Decode a pagination cursor produced by :func:`_encode_cursor`.

    Args:
        cursor: URL-safe base-64 encoded cursor string.

    Returns:
        A tuple of ``(opened_at, trade_id)``.

    Raises:
        ValueError: If the cursor cannot be decoded or has an invalid
            format.
    """
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        ts_part, id_part = raw.split("|", 1)
        opened_at = datetime.fromisoformat(ts_part)
        trade_id = uuid.UUID(id_part)
    except (ValueError, binascii.Error) as exc:
        raise ValueError(f"Invalid pagination cursor: {cursor!r}") from exc
    return opened_at, trade_id


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

    async def create(self, data: TradeCreate) -> Trade:
        """Persist a new trade and return the flushed ORM instance.

        The session is *flushed* (so the database assigns server
        defaults) but not committed — the service layer is responsible
        for committing.

        Args:
            data: Validated trade creation payload.

        Returns:
            The newly created :class:`Trade` with all server defaults
            populated.
        """
        trade = Trade(**data.model_dump())
        self._session.add(trade)
        await self._session.flush()
        await self._session.refresh(trade)
        return trade

    async def get_by_id(self, trade_id: uuid.UUID) -> Trade | None:
        """Retrieve a single trade by its primary key.

        Args:
            trade_id: UUID of the trade to fetch.

        Returns:
            The matching :class:`Trade`, or ``None`` if not found.
        """
        result = await self._session.execute(select(Trade).where(Trade.id == trade_id))
        return result.scalar_one_or_none()

    async def list_cursor(
        self,
        limit: int = PAGINATION_DEFAULT_LIMIT,
        cursor: str | None = None,
        include_total: bool = False,
    ) -> tuple[list[Trade], str | None, int | None]:
        """Return a cursor-paginated page of trades.

        Trades are ordered by ``(opened_at DESC, id DESC)`` for stable
        pagination.  When a ``cursor`` is supplied the query applies a
        keyset filter so only rows *after* the cursor position are
        returned.

        Args:
            limit: Maximum number of items to return. Clamped to
                ``[1, PAGINATION_MAX_LIMIT]``.
            cursor: Opaque pagination cursor from a previous response.
            include_total: When ``True``, run an additional ``COUNT(*)``
                query and include the result in the return value.
                Defaults to ``False`` to avoid the extra query cost.

        Returns:
            A three-tuple of:

            - ``items``: list of :class:`Trade` instances (length ≤
              ``limit``).
            - ``next_cursor``: encoded cursor for the next page, or
              ``None`` if this is the last page.
            - ``total``: total row count across all pages, or ``None``
              when ``include_total`` is ``False``.

        Raises:
            ValueError: If the supplied cursor is malformed.
        """
        clamped_limit = max(1, min(limit, PAGINATION_MAX_LIMIT))

        stmt = select(Trade).order_by(Trade.opened_at.desc(), Trade.id.desc())

        if cursor is not None:
            cursor_opened_at, cursor_id = _decode_cursor(cursor)
            # Keyset pagination: rows that come *after* the cursor in the
            # chosen sort order (opened_at DESC, id DESC).
            stmt = stmt.where(
                (Trade.opened_at < cursor_opened_at)
                | ((Trade.opened_at == cursor_opened_at) & (Trade.id < cursor_id))
            )

        # Fetch one extra row to determine whether another page exists.
        stmt = stmt.limit(clamped_limit + 1)
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())

        has_more = len(rows) > clamped_limit
        items = rows[:clamped_limit]

        next_cursor: str | None = None
        if has_more and items:
            last = items[-1]
            # opened_at is always set; type narrowing for mypy.
            last_opened_at: datetime = last.opened_at
            if last_opened_at.tzinfo is None:
                last_opened_at = last_opened_at.replace(tzinfo=UTC)
            next_cursor = _encode_cursor(last_opened_at, last.id)

        # Count query — only executed when explicitly requested.
        # Reasonable for datasets up to ~1 M rows; skip by default.
        total: int | None = None
        if include_total:
            count_result = await self._session.execute(
                select(func.count()).select_from(Trade)
            )
            total = count_result.scalar_one_or_none()

        return items, next_cursor, total

    async def update(
        self,
        trade: Trade,
        data: TradeUpdate,
    ) -> Trade:
        """Apply a partial update to an existing trade.

        Only fields that are explicitly set in *data* (i.e. not
        ``None``) are written.  The session is flushed but not
        committed.

        Args:
            trade: The ORM instance to update (already loaded from DB).
            data: Validated partial update payload.

        Returns:
            The updated :class:`Trade` instance after flush.
        """
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(trade, field, value)
        self._session.add(trade)
        await self._session.flush()
        await self._session.refresh(trade)
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
