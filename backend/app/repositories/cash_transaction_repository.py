"""Async repository for the ``cash_transactions`` table.

All methods receive an :class:`AsyncSession` from the service layer and
return SQLAlchemy ORM instances.
"""

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.selectable import Select

from app.core.constants import PAGINATION_DEFAULT_LIMIT, PAGINATION_MAX_LIMIT
from app.models.cash_transaction import CashTransaction
from app.schemas.cash_transaction import (
    CashTransactionCreate,
    CashTransactionFilterParams,
    CashTransactionUpdate,
)


class CashTransactionRepository:
    """Data access layer for CashTransaction."""

    @staticmethod
    async def create(
        session: AsyncSession, create_schema: CashTransactionCreate
    ) -> CashTransaction:
        """Create a new cash transaction.

        Args:
            session: The database session.
            create_schema: The validated input data.

        Returns:
            The created CashTransaction ORM instance.
        """
        transaction = CashTransaction(**create_schema.model_dump())
        session.add(transaction)
        await session.flush()
        return transaction

    @staticmethod
    async def get(
        session: AsyncSession, transaction_id: uuid.UUID
    ) -> CashTransaction | None:
        """Retrieve a cash transaction by its ID.

        Args:
            session: The database session.
            transaction_id: The UUID of the transaction.

        Returns:
            The CashTransaction ORM instance or None if not found.
        """
        return await session.get(CashTransaction, transaction_id)

    @staticmethod
    async def get_by_account_id(
        session: AsyncSession,
        account_id: uuid.UUID,
        transaction_id: uuid.UUID,
    ) -> CashTransaction | None:
        """Retrieve a cash transaction by its ID, scoped to an account.

        Args:
            session: The database session.
            account_id: The UUID of the account.
            transaction_id: The UUID of the transaction.

        Returns:
            The CashTransaction ORM instance or None if not found.
        """
        stmt = select(CashTransaction).where(
            CashTransaction.id == transaction_id,
            CashTransaction.account_id == account_id,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_by_account(
        session: AsyncSession,
        account_id: uuid.UUID,
        filters: CashTransactionFilterParams,
        limit: int = PAGINATION_DEFAULT_LIMIT,
        offset: int = 0,
    ) -> Sequence[CashTransaction]:
        """List cash transactions for an account with optional filtering.

        Args:
            session: The database session.
            account_id: The UUID of the account.
            filters: Filter parameters.
            limit: Maximum number of records to return.
            offset: Number of records to skip.

        Returns:
            A sequence of CashTransaction ORM instances.
        """
        stmt = select(CashTransaction).where(CashTransaction.account_id == account_id)
        stmt = CashTransactionRepository._apply_filters(stmt, filters)
        stmt = stmt.order_by(CashTransaction.date.desc())

        limit = min(limit, PAGINATION_MAX_LIMIT)
        stmt = stmt.limit(limit).offset(offset)

        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def count_by_account(
        session: AsyncSession,
        account_id: uuid.UUID,
        filters: CashTransactionFilterParams,
    ) -> int:
        """Count cash transactions for an account matching the filters.

        Args:
            session: The database session.
            account_id: The UUID of the account.
            filters: Filter parameters.

        Returns:
            The total number of matching records.
        """
        stmt = select(func.count(CashTransaction.id)).where(
            CashTransaction.account_id == account_id
        )
        stmt = CashTransactionRepository._apply_filters(stmt, filters)

        result = await session.execute(stmt)
        return result.scalar_one()

    @staticmethod
    def _apply_filters(
        stmt: Select[Any], filters: CashTransactionFilterParams
    ) -> Select[Any]:
        """Apply filters to a select statement."""
        if filters.type is not None:
            stmt = stmt.where(CashTransaction.type == filters.type)
        if filters.symbol is not None:
            stmt = stmt.where(CashTransaction.symbol == filters.symbol)
        if filters.from_date is not None:
            stmt = stmt.where(CashTransaction.date >= filters.from_date)
        if filters.to_date is not None:
            stmt = stmt.where(CashTransaction.date <= filters.to_date)
        return stmt

    @staticmethod
    async def update(
        session: AsyncSession,
        transaction: CashTransaction,
        update_schema: CashTransactionUpdate,
    ) -> CashTransaction:
        """Update an existing cash transaction.

        Args:
            session: The database session.
            transaction: The existing CashTransaction ORM instance.
            update_schema: The validated update data.

        Returns:
            The updated CashTransaction ORM instance.
        """
        update_data = update_schema.model_dump(exclude_unset=True)
        if not update_data:
            return transaction

        for key, value in update_data.items():
            setattr(transaction, key, value)

        session.add(transaction)
        await session.flush()
        return transaction

    @staticmethod
    async def delete(session: AsyncSession, transaction_id: uuid.UUID) -> None:
        """Delete a cash transaction.

        Args:
            session: The database session.
            transaction_id: The UUID of the transaction.
        """
        stmt = delete(CashTransaction).where(CashTransaction.id == transaction_id)
        await session.execute(stmt)
