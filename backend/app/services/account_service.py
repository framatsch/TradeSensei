"""Business-logic service for trading account operations.

Provides CRUD operations on broker accounts, always scoped to the
authenticated user for data isolation.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AccountNotFoundError
from app.repositories.account_repository import AccountRepository
from app.schemas.account import (
    AccountCreate,
    AccountMetrics,
    AccountRead,
    AccountSettings,
    AccountUpdate,
)
from app.schemas.common import CursorPage
from app.utils.encryption import encrypt_token


def _build_account_read(account: object, has_props: bool) -> AccountRead:
    """Build an :class:`AccountRead` DTO from an ORM instance.

    Converts the raw JSONB ``settings`` dict to an :class:`AccountSettings`
    object and sets the computed ``has_api_keys`` flag.

    Args:
        account: The ORM :class:`~app.models.account.Account` instance.
        has_props: Whether the account has stored broker credentials.

    Returns:
        A fully populated :class:`AccountRead` DTO.
    """
    item = AccountRead.model_validate(account)
    # Deserialise the JSONB settings blob — fall back to defaults if absent.
    raw_settings = getattr(account, "settings", None)
    if raw_settings:
        item.settings = AccountSettings.model_validate(raw_settings)
    else:
        item.settings = AccountSettings()
    item.has_api_keys = has_props
    portfolio = getattr(account, "portfolio", None)
    if portfolio is not None:
        item.portfolio_name = getattr(portfolio, "name", None)
    return item


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

    async def list_accounts(
        self,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID | None = None,
    ) -> CursorPage[AccountRead]:
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
        accounts = await self._repo.list_by_user(user_id, portfolio_id)
        items: list[AccountRead] = [
            _build_account_read(a, len(a.properties) > 0) for a in accounts
        ]
        return CursorPage[AccountRead](
            items=items,
            next_cursor=None,
            total=len(items),
        )

    async def get_account(
        self,
        account_id: uuid.UUID,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID | None = None,
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
        account = await self._repo.get_by_id(account_id, user_id, portfolio_id)
        if account is None:
            raise AccountNotFoundError(f"Account {account_id} not found.")
        return _build_account_read(account, len(account.properties) > 0)

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
                await self._repo.upsert_property(
                    account.id,
                    user_id,
                    key,
                    encrypt_token(value),
                )
        # Persist settings if provided
        if data.settings is not None:
            await self._repo.update_settings(account.id, user_id, data.settings)
        await self._session.commit()
        # Re-fetch with selectinload so that account.properties is eagerly
        # loaded in the async context — bare refresh() does not load relations.
        refreshed = await self._repo.get_by_id(account.id, user_id)
        if refreshed is None:
            raise RuntimeError(
                f"Account {account.id} disappeared after creation/update."
            )
        return _build_account_read(refreshed, len(refreshed.properties) > 0)

    async def update_account(
        self,
        account_id: uuid.UUID,
        data: AccountUpdate,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID | None = None,
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
        account = await self._repo.get_by_id(account_id, user_id, portfolio_id)
        if account is None:
            raise AccountNotFoundError(f"Account {account_id} not found.")
        updated = await self._repo.update(account, data)
        if data.properties:
            for key, value in data.properties.items():
                await self._repo.upsert_property(
                    updated.id,
                    user_id,
                    key,
                    encrypt_token(value),
                )
        # Persist settings if provided (merge with existing via repo)
        if data.settings is not None:
            await self._repo.update_settings(updated.id, user_id, data.settings)
        await self._session.commit()
        # Re-fetch with selectinload so that updated.properties is eagerly
        # loaded in the async context — bare refresh() does not load relations.
        refreshed = await self._repo.get_by_id(updated.id, user_id)
        if refreshed is None:
            raise RuntimeError(
                f"Account {updated.id} disappeared after creation/update."
            )
        return _build_account_read(refreshed, len(refreshed.properties) > 0)

    async def delete_account(
        self,
        account_id: uuid.UUID,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID | None = None,
    ) -> None:
        """Delete an account owned by the given user.

        Args:
            account_id: UUID of the account to delete.
            user_id: UUID of the authenticated user.

        Raises:
            :class:`~app.core.exceptions.AccountNotFoundError`: If no
                account with that ID exists for the requesting user.
        """
        account = await self._repo.get_by_id(account_id, user_id, portfolio_id)
        if account is None:
            raise AccountNotFoundError(f"Account {account_id} not found.")
        await self._repo.delete(account)
        await self._session.commit()

    async def get_metrics(
        self,
        account_id: uuid.UUID,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID | None = None,
    ) -> AccountMetrics:
        """Calculate and return aggregate cash metrics for a single account.

        Args:
            account_id: UUID of the account.
            user_id: UUID of the authenticated user.

        Returns:
            An :class:`~app.schemas.account.AccountMetrics` DTO.

        Raises:
            :class:`~app.core.exceptions.AccountNotFoundError`: If no
                account with that ID exists for the requesting user.
        """
        account = await self._repo.get_by_id(account_id, user_id, portfolio_id)
        if account is None:
            raise AccountNotFoundError(f"Account {account_id} not found.")

        return await self._repo.get_metrics(account_id, user_id)
