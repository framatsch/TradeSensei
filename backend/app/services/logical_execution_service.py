"""Service for translating broker raw transactions into logical executions.

This service implements the raw-to-logical translation layer:

1. For every new :class:`~app.models.broker_raw_transaction.BrokerRawTransaction`
   that was just inserted, it creates a corresponding
   :class:`~app.models.logical_execution.LogicalExecution` with
   ``status = ExecutionStatus.IMPORTED`` (1:1 mapping).
2. It links the two records via a
   :class:`~app.models.transaction_execution_mapping.TransactionExecutionMapping`
   row.

No business logic beyond the 1:1 translation lives here.  Merging, splitting,
and manual creation of logical executions will be separate operations.
"""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.broker_raw_transaction import BrokerRawTransaction
from app.models.logical_execution import ExecutionStatus, LogicalExecution
from app.models.transaction_execution_mapping import TransactionExecutionMapping

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

    async def create_from_raw(
        self,
        raw: BrokerRawTransaction,
    ) -> LogicalExecution | None:
        """Create a logical execution from a single raw transaction.

        Produces a 1:1 :class:`~app.models.logical_execution.LogicalExecution`
        with ``status = imported`` and a corresponding
        :class:`~app.models.transaction_execution_mapping.TransactionExecutionMapping`
        linking the two records.

        If a logical execution already exists for this raw transaction (i.e.
        re-import scenario where the raw row was already there but no logical
        execution was created), the method skips creation and returns ``None``.

        The session is **not** flushed or committed here — the caller controls
        the transaction boundary.

        Args:
            raw: A persisted (flushed)
                :class:`~app.models.broker_raw_transaction.BrokerRawTransaction`
                row.

        Returns:
            The newly created :class:`~app.models.logical_execution.LogicalExecution`,
            or ``None`` if a logical execution already exists for this raw
            transaction.
        """
        # Check if a mapping already exists for this raw transaction.
        existing = await self._session.execute(
            select(TransactionExecutionMapping).where(
                TransactionExecutionMapping.raw_transaction_id == raw.id
            )
        )
        if existing.scalar_one_or_none() is not None:
            logger.debug(
                "Logical execution already exists for raw transaction %s — skipping.",
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
            status=ExecutionStatus.IMPORTED,
            multiplier=raw.multiplier,
        )
        self._session.add(logical)
        await self._session.flush()  # get the server-generated UUID

        mapping = TransactionExecutionMapping(
            raw_transaction_id=raw.id,
            logical_execution_id=logical.id,
        )
        self._session.add(mapping)

        logger.debug(
            "Created logical execution %s from raw transaction %s.",
            logical.id,
            raw.id,
        )
        return logical

    async def bulk_create_from_raw(
        self,
        raw_transactions: list[BrokerRawTransaction],
    ) -> list[LogicalExecution]:
        """Create logical executions for a batch of raw transactions.

        Calls :meth:`create_from_raw` for each record in ``raw_transactions``.
        Records for which a logical execution already exists are silently
        skipped.

        The session is **not** committed here — the caller controls the
        transaction boundary.

        Args:
            raw_transactions: List of persisted (flushed)
                :class:`~app.models.broker_raw_transaction.BrokerRawTransaction`
                rows.

        Returns:
            List of newly created
            :class:`~app.models.logical_execution.LogicalExecution` instances
            (excludes skipped duplicates).
        """
        created: list[LogicalExecution] = []
        for raw in raw_transactions:
            logical = await self.create_from_raw(raw)
            if logical is not None:
                created.append(logical)

        logger.info(
            "bulk_create_from_raw: created %d logical executions "
            "from %d raw transactions (%d skipped as duplicates).",
            len(created),
            len(raw_transactions),
            len(raw_transactions) - len(created),
        )
        return created

    async def get_logical_for_raw(self, raw_id: str) -> list[LogicalExecution]:
        """Return all logical executions linked to a raw transaction.

        Args:
            raw_id: Primary key of the
                :class:`~app.models.broker_raw_transaction.BrokerRawTransaction`.

        Returns:
            List of linked :class:`~app.models.logical_execution.LogicalExecution`
            instances (usually one for ``imported`` status).
        """
        stmt = (
            select(LogicalExecution)
            .join(
                TransactionExecutionMapping,
                TransactionExecutionMapping.logical_execution_id == LogicalExecution.id,
            )
            .where(TransactionExecutionMapping.raw_transaction_id == raw_id)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        account_id: uuid.UUID | None = None,
        status: ExecutionStatus | None = None,
    ) -> list[LogicalExecution]:
        """Return all logical executions for a user.

        Args:
            user_id: UUID of the owning user.
            account_id: Optional account filter.
            status: Optional status filter.

        Returns:
            List of :class:`~app.models.logical_execution.LogicalExecution`
            ordered by ``executed_at`` ascending.
        """
        stmt = (
            select(LogicalExecution)
            .outerjoin(
                TransactionExecutionMapping,
                TransactionExecutionMapping.logical_execution_id == LogicalExecution.id,
            )
            .outerjoin(
                BrokerRawTransaction,
                BrokerRawTransaction.id
                == TransactionExecutionMapping.raw_transaction_id,
            )
            .where(LogicalExecution.user_id == user_id)
            .order_by(LogicalExecution.executed_at, BrokerRawTransaction.id)
        )
        if account_id is not None:
            stmt = stmt.where(LogicalExecution.account_id == account_id)
        if status is not None:
            stmt = stmt.where(LogicalExecution.status == status)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
