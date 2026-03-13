"""Async repository for the ``accounts`` table.

All methods receive an :class:`AsyncSession` from the service layer and
are scoped to a specific ``user_id`` for data isolation.  No business
logic lives here.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.schemas.account import AccountCreate, AccountUpdate


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

        Args:
            account_id: UUID of the account to fetch.
            user_id: UUID of the requesting user — enforces isolation.

        Returns:
            The matching :class:`Account`, or ``None`` if not found or
            not owned by the given user.
        """
        result = await self._session.execute(
            select(Account).where(
                Account.id == account_id,
                Account.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: uuid.UUID) -> list[Account]:
        """Return all accounts owned by the given user.

        Results are ordered by ``created_at`` ascending so the list is
        stable across calls.

        Args:
            user_id: UUID of the user whose accounts to list.

        Returns:
            A list of :class:`Account` ORM instances (may be empty).
        """
        result = await self._session.execute(
            select(Account)
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
            broker=data.broker,
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
        The session is flushed but not committed.

        Args:
            account: The ORM instance to update.
            data: Validated partial update payload.

        Returns:
            The updated :class:`Account` instance after flush.
        """
        update_dict = data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(account, field, value)
        self._session.add(account)
        await self._session.flush()
        await self._session.refresh(account)
        return account

    async def delete(self, account: Account) -> None:
        """Delete an account from the database.

        The session is flushed but not committed.

        Args:
            account: The ORM instance to delete.
        """
        await self._session.delete(account)
        await self._session.flush()
