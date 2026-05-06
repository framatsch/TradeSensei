"""Async repository for the ``accounts`` table.

All methods receive an :class:`AsyncSession` from the service layer and
are scoped to a specific ``user_id`` for data isolation.  No business
logic lives here.
"""

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy import update as sa_update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.account import Account
from app.models.account_property import AccountProperty
from app.models.cash_transaction import CashTransaction, CashTransactionType
from app.models.portfolio import Portfolio
from app.schemas.account import (
    AccountCreate,
    AccountMetrics,
    AccountSettings,
    AccountUpdate,
)


class AccountRepository:
    """Data-access object for the ``accounts`` table.

    Every query is scoped to a ``user_id`` so that users can never see
    or modify each other's accounts.

    Args:
        session: An open :class:`AsyncSession` managed by the caller.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the repository with an existing session.

        Args:
            session: The database session to use for all queries.
        """
        self._session = session

    async def get_by_id(
        self,
        account_id: uuid.UUID,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID | None = None,
    ) -> Account | None:
        """Retrieve a single account by primary key, scoped to a user.

        Eagerly loads associated :class:`~app.models.account_property.AccountProperty`
        records so that the service layer can inspect them without additional
        round-trips.

        Args:
            account_id: UUID of the account to fetch.
            user_id: UUID of the requesting user — enforces isolation.

        Returns:
            The matching :class:`Account`, or ``None`` if not found or
            not owned by the given user.
        """
        stmt = (
            select(Account)
            .options(
                selectinload(Account.properties),
                selectinload(Account.portfolio),
            )
            .join(Portfolio, Account.portfolio_id == Portfolio.id)
            .where(
                Account.id == account_id,
                Portfolio.user_id == user_id,
            )
        )
        if portfolio_id is not None:
            stmt = stmt.where(Account.portfolio_id == portfolio_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_with_properties(
        self,
        account_id: uuid.UUID,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID | None = None,
    ) -> Account | None:
        """Retrieve an account by ID with eagerly loaded properties.

        Args:
            account_id: UUID of the account to fetch.
            user_id: UUID of the requesting user.

        Returns:
            Matching account or ``None``.
        """
        return await self.get_by_id(account_id, user_id, portfolio_id)

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID | None = None,
    ) -> list[Account]:
        """Return all accounts owned by the given user.

        Eagerly loads associated :class:`~app.models.account_property.AccountProperty`
        records so that the service layer can compute ``has_api_keys`` without
        additional round-trips.

        Results are ordered by ``created_at`` ascending so the list is
        stable across calls.

        Args:
            user_id: UUID of the user whose accounts to list.

        Returns:
            A list of :class:`Account` ORM instances (may be empty).
        """
        stmt = (
            select(Account)
            .options(
                selectinload(Account.properties),
                selectinload(Account.portfolio),
            )
            .where(Account.user_id == user_id)
            .order_by(Account.created_at.asc())
        )
        if portfolio_id is not None:
            stmt = stmt.where(Account.portfolio_id == portfolio_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, data: AccountCreate, user_id: uuid.UUID) -> Account:
        """Persist a new account and return the flushed ORM instance.

        The session is *flushed* so the database assigns server defaults
        but not committed — the service layer commits.

        Args:
            data: Validated account creation payload.
            user_id: UUID of the owning user.

        Returns:
            The newly created :class:`Account` with all server defaults
            populated.
        """
        portfolio_row = await self._session.execute(
            select(Portfolio.id, Portfolio.base_currency).where(
                Portfolio.id == data.portfolio_id,
                Portfolio.user_id == user_id,
            )
        )
        portfolio_result = portfolio_row.one_or_none()
        if portfolio_result is None:
            raise ValueError("Portfolio not found.")

        account = Account(
            user_id=user_id,
            portfolio_id=data.portfolio_id,
            name=data.name,
            type=data.type,
            currency=portfolio_result.base_currency,
        )
        self._session.add(account)
        await self._session.flush()
        await self._session.refresh(account)
        return account

    async def update(
        self,
        account: Account,
        data: AccountUpdate,
    ) -> Account:
        """Apply a partial update to an existing account.

        Only fields explicitly set in *data* (non-``None``) are written.
        The ``properties`` field is excluded here — it is handled separately
        by the service layer via :meth:`upsert_property`.
        The session is flushed but not committed.

        Args:
            account: The ORM instance to update.
            data: Validated partial update payload.

        Returns:
            The updated :class:`Account` instance after flush.
        """
        update_dict = data.model_dump(exclude_unset=True, exclude={"properties"})
        for field, value in update_dict.items():
            setattr(account, field, value)
        self._session.add(account)
        await self._session.flush()
        await self._session.refresh(account)
        return account

    async def update_settings(
        self,
        account_id: uuid.UUID,
        user_id: uuid.UUID,
        settings: AccountSettings,
    ) -> None:
        """Persist import/sync settings for an account as a JSONB blob.

        Merges the provided settings with any existing settings stored on
        the row (right-hand value wins on conflict).  The session is
        flushed but not committed — the caller is responsible for the
        transaction boundary.

        Args:
            account_id: UUID of the account to update.
            settings: Validated :class:`AccountSettings` to persist.
        """
        settings_dict: dict[str, Any] = settings.model_dump()
        stmt = (
            sa_update(Account)
            .where(Account.id == account_id, Account.user_id == user_id)
            .values(settings=settings_dict)
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def upsert_property(
        self,
        account_id: uuid.UUID,
        user_id: uuid.UUID,
        key: str,
        encrypted_value: str,
    ) -> None:
        """Insert or update a single AccountProperty row.

        See :class:`~app.models.account_property.AccountProperty`.

        Uses a PostgreSQL ``INSERT ... ON CONFLICT DO UPDATE`` so this
        method is idempotent — calling it multiple times with the same key
        overwrites the stored value.  The session is not committed here;
        the caller (service layer) is responsible for committing.

        Args:
            account_id: UUID of the owning account.
            key: Property key identifier (e.g. ``"SCHWAB_APP_KEY"``).
            encrypted_value: Fernet-encrypted property value.
        """
        owner_check = await self._session.execute(
            select(Account.id).where(
                Account.id == account_id,
                Account.user_id == user_id,
            )
        )
        if owner_check.scalar_one_or_none() is None:
            return

        stmt = pg_insert(AccountProperty).values(
            account_id=account_id,
            key=key,
            value=encrypted_value,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_account_properties_account_key",
            set_={"value": encrypted_value},
        )
        await self._session.execute(stmt)

    async def delete(self, account: Account) -> None:
        """Delete an account from the database.

        The session is flushed but not committed.

        Args:
            account: The ORM instance to delete.
        """
        await self._session.delete(account)
        await self._session.flush()

    async def get_metrics(
        self,
        account_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> AccountMetrics:
        """Calculate aggregate cash flow metrics for the account.

        Args:
            account_id: The account ID.
            user_id: The owner user ID (for scope).

        Returns:
            An AccountMetrics DTO with total dividends and withholding tax in EUR.
        """
        # Ensure account belongs to user
        stmt = (
            select(
                CashTransaction.type,
                func.sum(
                    func.coalesce(CashTransaction.amount_eur, CashTransaction.amount)
                ).label("total"),
            )
            .join(Account)
            .where(
                Account.id == account_id,
                Account.user_id == user_id,
                CashTransaction.type.in_(
                    [CashTransactionType.DIVIDEND, CashTransactionType.WITHHOLDING_TAX]
                ),
            )
            .group_by(CashTransaction.type)
        )
        result = await self._session.execute(stmt)
        totals = {row.type: row.total for row in result}

        return AccountMetrics(
            total_dividends=totals.get(CashTransactionType.DIVIDEND, Decimal("0.0")),
            total_withholding_tax=totals.get(
                CashTransactionType.WITHHOLDING_TAX, Decimal("0.0")
            ),
        )
