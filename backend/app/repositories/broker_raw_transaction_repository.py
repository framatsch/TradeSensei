"""Async repository for the ``broker_raw_transactions`` table.

All methods receive an :class:`AsyncSession` from the service layer and
return SQLAlchemy ORM instances.  No business logic lives here.
"""

import uuid

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.broker_raw_transaction import BrokerRawTransaction
from app.schemas.broker_raw_transaction import BrokerRawTransactionCreate


class BrokerRawTransactionRepository:
    """Data-access layer for
    :class:`~app.models.broker_raw_transaction.BrokerRawTransaction`.

    All write operations use ``ON CONFLICT DO NOTHING`` (idempotent upsert)
    so that re-importing the same file never creates duplicate rows.

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

    async def upsert(
        self,
        data: BrokerRawTransactionCreate,
    ) -> BrokerRawTransaction | None:
        """Insert a raw transaction record, ignoring conflicts on ``id``.

        If a row with the same ``id`` already exists (re-import), the insert
        is silently skipped and ``None`` is returned.  The caller must flush /
        commit the outer transaction.

        Args:
            data: Validated raw transaction payload.  ``user_id`` and
                ``account_id`` must be set before calling this method.

        Returns:
            The newly created
            :class:`~app.models.broker_raw_transaction.BrokerRawTransaction`
            instance, or ``None`` if the row already existed.
        """
        stmt = (
            pg_insert(BrokerRawTransaction)
            .values(**data.model_dump())
            .on_conflict_do_nothing(index_elements=["id"])
            .returning(BrokerRawTransaction)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return row

    async def bulk_upsert(
        self,
        records: list[BrokerRawTransactionCreate],
    ) -> list[str]:
        """Insert multiple raw transaction records, ignoring conflicts.

        Processes records one-by-one to capture which IDs were newly inserted
        vs already existing.  For large imports a single bulk statement would be
        faster, but per-row processing allows accurate accounting.

        Args:
            records: List of validated raw transaction payloads.

        Returns:
            List of ``id`` strings for records that were newly inserted
            (i.e. not already in the DB).
        """
        inserted_ids: list[str] = []
        for rec in records:
            row = await self.upsert(rec)
            if row is not None:
                inserted_ids.append(rec.id)
        return inserted_ids

    async def get_by_id(self, raw_id: str) -> BrokerRawTransaction | None:
        """Retrieve a single raw transaction by its primary key.

        Args:
            raw_id: Composite broker execution ID (e.g. ``"ibkr:2277515525"``).

        Returns:
            The matching
            :class:`~app.models.broker_raw_transaction.BrokerRawTransaction`,
            or ``None`` if not found.
        """
        stmt = select(BrokerRawTransaction).where(BrokerRawTransaction.id == raw_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        account_id: uuid.UUID | None = None,
    ) -> list[BrokerRawTransaction]:
        """Return all raw transactions for a user, optionally filtered by account.

        Args:
            user_id: UUID of the owning user.
            account_id: Optional account filter.

        Returns:
            List of :class:`~app.models.broker_raw_transaction.BrokerRawTransaction`
            ordered by ``executed_at`` ascending.
        """
        stmt = (
            select(BrokerRawTransaction)
            .where(BrokerRawTransaction.user_id == user_id)
            .order_by(BrokerRawTransaction.executed_at)
        )
        if account_id is not None:
            stmt = stmt.where(BrokerRawTransaction.account_id == account_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_existing_ids(
        self,
        user_id: uuid.UUID,
        account_id: uuid.UUID | None = None,
    ) -> set[str]:
        """Return the set of existing raw transaction IDs for a user/account.

        Used by the import service for fast deduplication without loading full
        rows.

        Args:
            user_id: UUID of the owning user.
            account_id: Optional account filter.

        Returns:
            Set of ``id`` strings already in the database.
        """
        stmt = select(BrokerRawTransaction.id).where(
            BrokerRawTransaction.user_id == user_id
        )
        if account_id is not None:
            stmt = stmt.where(BrokerRawTransaction.account_id == account_id)
        result = await self._session.execute(stmt)
        return set(result.scalars().all())

    async def delete_by_user_account(
        self,
        user_id: uuid.UUID,
        account_id: uuid.UUID,
    ) -> int:
        """Delete all raw transactions for a user/account pair.

        Args:
            user_id: UUID of the owning user.
            account_id: UUID of the account to clear.

        Returns:
            Number of deleted rows.
        """
        stmt = (
            delete(BrokerRawTransaction)
            .where(
                BrokerRawTransaction.user_id == user_id,
                BrokerRawTransaction.account_id == account_id,
            )
            .returning(BrokerRawTransaction.id)
        )
        result = await self._session.execute(stmt)
        deleted = list(result.scalars().all())
        await self._session.flush()
        return len(deleted)
