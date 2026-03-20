"""Async repository for the ``accounts`` table.

All methods receive an :class:`AsyncSession` from the service layer and
are scoped to a specific ``user_id`` for data isolation.  No business
logic lives here.
"""

import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.account import Account
from app.models.cash_transaction import CashTransaction, CashTransactionType
from app.schemas.account import AccountCreate, AccountMetrics, AccountUpdate


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
        result = await self._session.execute(
            select(Account)
            .options(selectinload(Account.properties))
            .where(
                Account.id == account_id,
                Account.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: uuid.UUID) -> list[Account]:
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
        result = await self._session.execute(
            select(Account)
            .options(selectinload(Account.properties))
            .where(Account.user_id == user_id)
            .order_by(Account.created_at.asc())
        )
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
        account = Account(
            user_id=user_id,
            name=data.name,
            type=data.type,
            currency=data.currency,
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

    async def upsert_property(
        self,
        account_id: uuid.UUID,
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
        from app.models.account_property import AccountProperty

        stmt = (
            pg_insert(AccountProperty)
            .values(account_id=account_id, key=key, value=encrypted_value)
            .on_conflict_do_update(
                constraint="uq_account_properties_account_key",
                set_={"value": encrypted_value},
            )
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
                func.sum(func.coalesce(CashTransaction.amount_eur, 0)).label("total"),
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
