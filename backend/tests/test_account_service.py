"""Unit tests for AccountService — no database access (all repository calls mocked).

Every test patches :class:`~app.repositories.account_repository.AccountRepository`
methods directly on the instance created inside
:class:`~app.services.account_service.AccountService`.  No real database
connection is required.

Isolation strategy: ``AccountService.__init__`` creates an
``AccountRepository`` from the injected session.  We replace individual
methods with :class:`~unittest.mock.AsyncMock` after construction, which
gives precise control over each test scenario.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import AccountNotFoundError
from app.models.account import Account, AccountType
from app.schemas.account import AccountCreate, AccountRead, AccountUpdate
from app.schemas.common import CursorPage
from app.services.account_service import AccountService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_account(
    *,
    id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    name: str = "IBKR Main",
    account_type: AccountType = AccountType.MANUAL,
    currency: str = "USD",
    is_active: bool = True,
) -> Account:
    """Build a detached :class:`Account` ORM instance for test use.

    Args:
        id: UUID primary key. Defaults to a new random UUID.
        user_id: UUID of the owning user. Defaults to a new random UUID.
        name: Account label. Defaults to ``"IBKR Main"``.
        account_type: Account/broker type. Defaults to ``AccountType.MANUAL``.
        currency: ISO-4217 currency code. Defaults to ``"USD"``.
        is_active: Whether the account is active. Defaults to ``True``.

    Returns:
        An :class:`Account` instance with all required fields populated.
    """
    account = Account()
    account.id = id if id is not None else uuid.uuid4()  # type: ignore[assignment]
    account.user_id = user_id if user_id is not None else uuid.uuid4()  # type: ignore[assignment]
    account.name = name  # type: ignore[assignment]
    account.type = account_type  # type: ignore[assignment]
    account.currency = currency  # type: ignore[assignment]
    account.is_active = is_active  # type: ignore[assignment]
    account.created_at = datetime.now(UTC)  # type: ignore[assignment]
    account.updated_at = datetime.now(UTC)  # type: ignore[assignment]
    account.properties = []  # type: ignore[assignment]
    return account


@pytest.fixture()
def mock_session() -> AsyncMock:
    """Return a mock :class:`AsyncSession`.

    Returns:
        A fresh :class:`AsyncMock` standing in for the SQLAlchemy session.
    """
    return AsyncMock()


@pytest.fixture()
def service(mock_session: AsyncMock) -> AccountService:
    """Return an :class:`AccountService` wired to a mock session.

    Args:
        mock_session: The mocked SQLAlchemy session.

    Returns:
        An :class:`AccountService` instance ready for testing.
    """
    return AccountService(mock_session)


# ---------------------------------------------------------------------------
# List tests
# ---------------------------------------------------------------------------


class TestListAccounts:
    """Unit tests for :meth:`AccountService.list_accounts`."""

    @pytest.mark.unit
    async def test_list_accounts_returns_list(self, service: AccountService) -> None:
        """list_accounts() must return a CursorPage whose items are AccountRead DTOs.

        When the repository returns a non-empty list of accounts the
        service must map them to :class:`~app.schemas.account.AccountRead`
        DTOs and wrap them in a :class:`~app.schemas.common.CursorPage`.
        """
        user_id = uuid.uuid4()
        accounts = [
            _make_account(user_id=user_id, name="Account A"),
            _make_account(user_id=user_id, name="Account B"),
        ]
        service._repo.list_by_user = AsyncMock(return_value=accounts)  # type: ignore[method-assign]

        result = await service.list_accounts(user_id)

        assert isinstance(result, CursorPage)
        assert result.total == 2
        assert len(result.items) == 2
        assert all(isinstance(item, AccountRead) for item in result.items)

    @pytest.mark.unit
    async def test_list_accounts_returns_empty_page(
        self, service: AccountService
    ) -> None:
        """list_accounts() must return a CursorPage with zero items when none exist.

        An empty repository response must map cleanly to an empty page
        rather than raising an exception.
        """
        user_id = uuid.uuid4()
        service._repo.list_by_user = AsyncMock(return_value=[])  # type: ignore[method-assign]

        result = await service.list_accounts(user_id)

        assert result.total == 0
        assert result.items == []
        assert result.next_cursor is None


# ---------------------------------------------------------------------------
# Get single account tests
# ---------------------------------------------------------------------------


class TestGetAccount:
    """Unit tests for :meth:`AccountService.get_account`."""

    @pytest.mark.unit
    async def test_get_account_success(self, service: AccountService) -> None:
        """get_account() must return an AccountRead DTO when the account exists.

        The returned DTO must carry the same ``id`` and ``name`` as the
        mock account returned by the repository.
        """
        user_id = uuid.uuid4()
        account = _make_account(user_id=user_id, name="My Account")
        service._repo.get_by_id = AsyncMock(return_value=account)  # type: ignore[method-assign]

        result = await service.get_account(account.id, user_id)  # type: ignore[arg-type]

        assert isinstance(result, AccountRead)
        assert result.id == account.id  # type: ignore[comparison-overlap]
        assert result.name == "My Account"

    @pytest.mark.unit
    async def test_get_account_not_found_raises(self, service: AccountService) -> None:
        """get_account() must raise AccountNotFoundError when the account is missing.

        When the repository returns ``None`` (account absent or owned by a
        different user), the service must raise
        :class:`~app.core.exceptions.AccountNotFoundError`.
        """
        service._repo.get_by_id = AsyncMock(return_value=None)  # type: ignore[method-assign]

        with pytest.raises(AccountNotFoundError):
            await service.get_account(uuid.uuid4(), uuid.uuid4())


# ---------------------------------------------------------------------------
# Create account tests
# ---------------------------------------------------------------------------


class TestCreateAccount:
    """Unit tests for :meth:`AccountService.create_account`."""

    @pytest.mark.unit
    async def test_create_account_success(self, service: AccountService) -> None:
        """create_account() must return an AccountRead DTO for the new account.

        The service should delegate to the repository and convert the
        returned ORM instance into a response DTO.
        """
        user_id = uuid.uuid4()
        payload = AccountCreate(name="New Account", type="schwab", currency="USD")
        created = _make_account(
            user_id=user_id, name="New Account", account_type=AccountType.SCHWAB
        )
        service._repo.create = AsyncMock(return_value=created)  # type: ignore[method-assign]
        service._repo.upsert_property = AsyncMock()  # type: ignore[method-assign]

        result = await service.create_account(payload, user_id)

        assert isinstance(result, AccountRead)
        assert result.name == "New Account"
        assert result.type == AccountType.SCHWAB
        service._repo.create.assert_awaited_once_with(payload, user_id)

    @pytest.mark.unit
    async def test_create_account_uses_default_currency(
        self, service: AccountService
    ) -> None:
        """create_account() must default currency to USD when not supplied.

        The :class:`~app.schemas.account.AccountCreate` schema defaults to
        ``"USD"``; the service must pass that through to the repository.
        """
        user_id = uuid.uuid4()
        payload = AccountCreate(name="USD Account")
        created = _make_account(user_id=user_id, name="USD Account", currency="USD")
        service._repo.create = AsyncMock(return_value=created)  # type: ignore[method-assign]

        result = await service.create_account(payload, user_id)

        assert result.currency == "USD"


# ---------------------------------------------------------------------------
# Update account tests
# ---------------------------------------------------------------------------


class TestUpdateAccount:
    """Unit tests for :meth:`AccountService.update_account`."""

    @pytest.mark.unit
    async def test_update_account_success(self, service: AccountService) -> None:
        """update_account() must return the updated AccountRead DTO.

        The service must first fetch the account, apply the update via the
        repository, and return the resulting DTO.
        """
        user_id = uuid.uuid4()
        original = _make_account(user_id=user_id, name="Old Name")
        updated = _make_account(
            id=original.id,  # type: ignore[arg-type]
            user_id=user_id,
            name="New Name",
        )
        service._repo.get_by_id = AsyncMock(return_value=original)  # type: ignore[method-assign]
        service._repo.update = AsyncMock(return_value=updated)  # type: ignore[method-assign]

        result = await service.update_account(
            original.id,  # type: ignore[arg-type]
            AccountUpdate(name="New Name"),
            user_id,
        )

        assert isinstance(result, AccountRead)
        assert result.name == "New Name"
        service._repo.update.assert_awaited_once()

    @pytest.mark.unit
    async def test_update_account_not_found_raises(
        self, service: AccountService
    ) -> None:
        """update_account() must raise AccountNotFoundError when the account is missing.

        When ``get_by_id`` returns ``None``, the service must raise
        :class:`~app.core.exceptions.AccountNotFoundError` and must
        **not** call ``update``.
        """
        service._repo.get_by_id = AsyncMock(return_value=None)  # type: ignore[method-assign]
        service._repo.update = AsyncMock()  # type: ignore[method-assign]

        with pytest.raises(AccountNotFoundError):
            await service.update_account(
                uuid.uuid4(), AccountUpdate(name="Anything"), uuid.uuid4()
            )

        service._repo.update.assert_not_called()


# ---------------------------------------------------------------------------
# Delete account tests
# ---------------------------------------------------------------------------


class TestDeleteAccount:
    """Unit tests for :meth:`AccountService.delete_account`."""

    @pytest.mark.unit
    async def test_delete_account_success(self, service: AccountService) -> None:
        """delete_account() must call the repository delete method exactly once.

        When the account exists, the service must call ``repo.delete``
        with the fetched ORM instance and return ``None``.
        """
        user_id = uuid.uuid4()
        account = _make_account(user_id=user_id)
        service._repo.get_by_id = AsyncMock(return_value=account)  # type: ignore[method-assign]
        service._repo.delete = AsyncMock()  # type: ignore[method-assign]

        result = await service.delete_account(account.id, user_id)  # type: ignore[arg-type]

        assert result is None
        service._repo.delete.assert_awaited_once_with(account)

    @pytest.mark.unit
    async def test_delete_account_not_found_raises(
        self, service: AccountService
    ) -> None:
        """delete_account() must raise AccountNotFoundError when the account is missing.

        When ``get_by_id`` returns ``None``, the service must raise
        :class:`~app.core.exceptions.AccountNotFoundError` and must
        **not** call ``delete``.
        """
        service._repo.get_by_id = AsyncMock(return_value=None)  # type: ignore[method-assign]
        service._repo.delete = AsyncMock()  # type: ignore[method-assign]

        with pytest.raises(AccountNotFoundError):
            await service.delete_account(uuid.uuid4(), uuid.uuid4())

        service._repo.delete.assert_not_called()
