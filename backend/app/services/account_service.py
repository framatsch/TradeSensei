"""Business-logic service for trading account operations.

Provides CRUD operations on broker accounts, always scoped to the
authenticated user for data isolation.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AccountNotFoundError
from app.repositories.account_repository import AccountRepository
from app.schemas.account import AccountCreate, AccountRead, AccountUpdate
from app.schemas.common import CursorPage


class AccountService:
    """Service layer for trading account management.

    All operations are scoped to a ``user_id`` so that users can only
    see and modify their own accounts.

    Args:
        session: An open :class:`AsyncSession` managed by the caller.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with a database session.

        Args:
            session: The session to use for all operations.
        """
        self._repo = AccountRepository(session)

    async def list_accounts(self, user_id: uuid.UUID) -> CursorPage[AccountRead]:
        """Return all accounts owned by the given user.

        Args:
            user_id: UUID of the authenticated user.

        Returns:
            A :class:`~app.schemas.common.CursorPage` of
            :class:`~app.schemas.account.AccountRead` DTOs.
            The full list is returned (no cursor pagination needed for
            a per-user account list, which is typically small).
        """
        # TODO: Implement true cursor-based pagination — currently all accounts
        # are returned in a single page without any cursor filtering.
        accounts = await self._repo.list_by_user(user_id)
        items = [AccountRead.model_validate(a) for a in accounts]
        return CursorPage[AccountRead](
            items=items,
            next_cursor=None,
            total=len(items),
        )

    async def get_account(
        self,
        account_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> AccountRead:
        """Retrieve a single account by ID, scoped to the requesting user.

        Args:
            account_id: UUID of the account to retrieve.
            user_id: UUID of the authenticated user.

        Returns:
            A :class:`~app.schemas.account.AccountRead` DTO.

        Raises:
            :class:`~app.core.exceptions.AccountNotFoundError`: If no
                account with that ID exists for the requesting user.
        """
        account = await self._repo.get_by_id(account_id, user_id)
        if account is None:
            raise AccountNotFoundError(f"Account {account_id} not found.")
        return AccountRead.model_validate(account)

    async def create_account(
        self,
        data: AccountCreate,
        user_id: uuid.UUID,
    ) -> AccountRead:
        """Create a new trading account for the given user.

        Args:
            data: Validated account creation payload.
            user_id: UUID of the authenticated user.

        Returns:
            A :class:`~app.schemas.account.AccountRead` DTO for the
            newly created account.
        """
        account = await self._repo.create(data, user_id)
        return AccountRead.model_validate(account)

    async def update_account(
        self,
        account_id: uuid.UUID,
        data: AccountUpdate,
        user_id: uuid.UUID,
    ) -> AccountRead:
        """Apply a partial update to an account owned by the given user.

        Args:
            account_id: UUID of the account to update.
            data: Validated partial update payload.
            user_id: UUID of the authenticated user.

        Returns:
            A :class:`~app.schemas.account.AccountRead` DTO reflecting
            the updated state.

        Raises:
            :class:`~app.core.exceptions.AccountNotFoundError`: If no
                account with that ID exists for the requesting user.
        """
        account = await self._repo.get_by_id(account_id, user_id)
        if account is None:
            raise AccountNotFoundError(f"Account {account_id} not found.")
        updated = await self._repo.update(account, data)
        return AccountRead.model_validate(updated)

    async def delete_account(
        self,
        account_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Delete an account owned by the given user.

        Args:
            account_id: UUID of the account to delete.
            user_id: UUID of the authenticated user.

        Raises:
            :class:`~app.core.exceptions.AccountNotFoundError`: If no
                account with that ID exists for the requesting user.
        """
        account = await self._repo.get_by_id(account_id, user_id)
        if account is None:
            raise AccountNotFoundError(f"Account {account_id} not found.")
        await self._repo.delete(account)
