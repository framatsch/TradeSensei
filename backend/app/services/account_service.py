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
from app.utils.encryption import encrypt_token


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
        self._session = session

    async def list_accounts(self, user_id: uuid.UUID) -> CursorPage[AccountRead]:
        """Return all accounts owned by the given user.

        Each :class:`~app.schemas.account.AccountRead` item has its
        ``has_api_keys`` flag set to ``True`` when the account has at least
        one stored :class:`~app.models.account_property.AccountProperty`.

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
        items: list[AccountRead] = []
        for a in accounts:
            item = AccountRead.model_validate(a)
            item.has_api_keys = len(a.properties) > 0
            items.append(item)
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

        The ``has_api_keys`` flag is set to ``True`` if the account has at
        least one stored :class:`~app.models.account_property.AccountProperty`.

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
        item = AccountRead.model_validate(account)
        item.has_api_keys = len(account.properties) > 0
        return item

    async def create_account(
        self,
        data: AccountCreate,
        user_id: uuid.UUID,
    ) -> AccountRead:
        """Create a new trading account for the given user.

        If ``data.properties`` is provided, each key-value pair is encrypted
        and persisted as an :class:`~app.models.account_property.AccountProperty`
        record.  Commits the session after all writes.

        Args:
            data: Validated account creation payload.
            user_id: UUID of the authenticated user.

        Returns:
            A :class:`~app.schemas.account.AccountRead` DTO for the
            newly created account.
        """
        account = await self._repo.create(data, user_id)
        if data.properties:
            for key, value in data.properties.items():
                await self._repo.upsert_property(account.id, key, encrypt_token(value))
        await self._session.commit()
        # Re-fetch with selectinload so that account.properties is eagerly
        # loaded in the async context — bare refresh() does not load relations.
        refreshed = await self._repo.get_by_id(account.id, user_id)
        assert refreshed is not None
        item = AccountRead.model_validate(refreshed)
        item.has_api_keys = len(refreshed.properties) > 0
        return item

    async def update_account(
        self,
        account_id: uuid.UUID,
        data: AccountUpdate,
        user_id: uuid.UUID,
    ) -> AccountRead:
        """Apply a partial update to an account owned by the given user.

        If ``data.properties`` is provided, each key-value pair is upserted
        (encrypted) as :class:`~app.models.account_property.AccountProperty`
        records.  Existing properties not included in the update payload are
        left unchanged.  Commits the session after all writes.

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
        if data.properties:
            for key, value in data.properties.items():
                await self._repo.upsert_property(updated.id, key, encrypt_token(value))
        await self._session.commit()
        # Re-fetch with selectinload so that updated.properties is eagerly
        # loaded in the async context — bare refresh() does not load relations.
        refreshed = await self._repo.get_by_id(updated.id, user_id)
        assert refreshed is not None
        item = AccountRead.model_validate(refreshed)
        item.has_api_keys = len(refreshed.properties) > 0
        return item

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
        await self._session.commit()
