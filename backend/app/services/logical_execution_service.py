"""Service for translating broker raw transactions into logical executions.

This service implements the raw-to-logical translation layer:

For every new :class:`~app.models.broker_raw_transaction.BrokerRawTransaction`
that was just inserted, it creates a corresponding
:class:`~app.models.logical_execution.LogicalExecution` with
``origin = 'imported'`` (1:1 mapping).

No business logic beyond the 1:1 translation lives here.  Merging, splitting,
and manual creation of logical executions will be separate operations.
"""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.broker_raw_transaction import BrokerRawTransaction
from app.models.logical_execution import (
    EXECUTION_ORIGIN_IMPORTED,
    LogicalExecution,
)
from app.repositories.execution import ExecutionRepository

logger = logging.getLogger(__name__)


class LogicalExecutionService:
    """Translates raw broker transactions into logical executions.

    Args:
        session: An open :class:`~sqlalchemy.ext.asyncio.AsyncSession`
            managed by the caller.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with a database session.

        Args:
            session: The session to use for all DB operations.
        """
        self._session = session
        self._execution_repo = ExecutionRepository(session)

    async def create_from_raw(
        self,
        raw: BrokerRawTransaction,
    ) -> LogicalExecution | None:
        """Create a logical execution from a single raw transaction.

        Produces a 1:1 :class:`~app.models.logical_execution.LogicalExecution`
        with ``origin = 'imported'``.

        Import deduplication checks:
        1. If ``raw.suppressed`` is True, skip unconditionally.

        Deduplication against already-imported BRTs is handled upstream by
        :meth:`~app.services.import_service.ImportService`: only newly inserted
        BRT rows (returned by the bulk upsert) are passed to this method, so
        no extra mapping lookup is needed.

        The session is **not** flushed or committed here — the caller controls
        the transaction boundary.

        Args:
            raw: A persisted (flushed)
                :class:`~app.models.broker_raw_transaction.BrokerRawTransaction`
                row.

        Returns:
            The newly created
            :class:`~app.models.logical_execution.LogicalExecution`,
            or ``None`` if skipped (suppressed BRT).
        """
        # Check 1: suppressed BRT — skip unconditionally
        if raw.suppressed:
            logger.debug(
                "Skipping suppressed raw transaction %s.",
                raw.id,
            )
            return None

        logical = LogicalExecution(
            user_id=raw.user_id,
            account_id=raw.account_id,
            symbol=raw.symbol,
            conid=raw.conid,
            asset_class=raw.asset_class,
            direction=raw.direction,
            quantity=raw.quantity,
            price=raw.price,
            commission=raw.commission,
            executed_at=raw.executed_at,
            pnl=raw.pnl,
            currency=raw.currency,
            origin=EXECUTION_ORIGIN_IMPORTED,
            multiplier=raw.multiplier,
        )
        self._session.add(logical)

        logger.debug(
            "Created logical execution for raw transaction %s.",
            raw.id,
        )
        return logical

    async def bulk_create_from_raw(
        self,
        raw_transactions: list[BrokerRawTransaction],
    ) -> tuple[list[LogicalExecution], int]:
        """Create logical executions for a batch of raw transactions.

        Calls :meth:`create_from_raw` for each record in ``raw_transactions``.
        Records that are suppressed are silently skipped.

        The session is **not** committed here — the caller controls the
        transaction boundary.

        Args:
            raw_transactions: List of persisted (flushed)
                :class:`~app.models.broker_raw_transaction.BrokerRawTransaction`
                rows.

        Returns:
            A tuple of:
            - List of newly created
              :class:`~app.models.logical_execution.LogicalExecution` instances.
            - Count of suppressed BRTs that were skipped.
        """
        created: list[LogicalExecution] = []
        suppressed_skipped = 0
        for raw in raw_transactions:
            if raw.suppressed:
                suppressed_skipped += 1
                continue
            logical = await self.create_from_raw(raw)
            if logical is not None:
                created.append(logical)

        logger.info(
            "bulk_create_from_raw: created %d logical executions from %d raw transactions (%d suppressed skipped).",
            len(created),
            len(raw_transactions),
            suppressed_skipped,
        )
        return created, suppressed_skipped

    async def get_logical_for_raw(self, raw_id: str) -> list[LogicalExecution]:
        """Return all logical executions linked to a raw transaction.

        Note: This method is a compatibility shim — with the simplified
        execution model, BRT-to-execution linkage is tracked by the BRT's
        ``suppressed`` flag rather than via a mapping table.  This method
        returns an empty list for now.

        Args:
            raw_id: Primary key of the
                :class:`~app.models.broker_raw_transaction.BrokerRawTransaction`.

        Returns:
            Empty list (mapping table no longer populated).
        """
        return []

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        account_id: uuid.UUID | None = None,
        origin: str | None = None,
        include_deleted: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[LogicalExecution]:
        """Return all logical executions for a user.

        Args:
            user_id: UUID of the owning user.
            account_id: Optional account filter.
            origin: Optional origin filter (imported|manual|merged|split).
            include_deleted: When False (default), excludes soft-deleted executions.
            limit: Optional max row count.
            offset: Number of rows to skip before reading.

        Returns:
            List of :class:`~app.models.logical_execution.LogicalExecution`
            ordered by ``executed_at`` ascending.
        """
        return await self._execution_repo.list_by_user(
            user_id=user_id,
            account_id=account_id,
            origin=origin,
            include_deleted=include_deleted,
            limit=limit,
            offset=offset,
        )
