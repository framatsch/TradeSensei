# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Account-centric broker sync service.

Dispatches remote sync and connection tests through the broker adapter
registry based on the :attr:`~app.models.account.AccountType` of the account.
Adapters only fetch broker payloads; every sync terminates in
:meth:`ImportService.import_trades() <app.services.import_service.ImportService.import_trades>`.
"""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AccountNotFoundError, ConfigurationError
from app.models.account import Account, AccountType
from app.repositories.account_repository import AccountRepository
from app.schemas.broker import (
    BrokerConnectionTestRequest,
    BrokerConnectionTestResult,
    BrokerStatusResponse,
    BrokerSyncResult,
)
from app.services.brokers.contracts import SyncWindow
from app.services.brokers.credentials import require_portfolio_id
from app.services.brokers.registry import adapter_for_account_type
from app.services.brokers.schwab.oauth import SchwabOAuth
from app.services.import_service import ImportService

logger = logging.getLogger(__name__)


class BrokerService:
    """Service layer for account-centric broker trade synchronisation.

    Broker credentials are loaded from encrypted
    :class:`~app.models.account_property.AccountProperty` records on the
    account by the resolved broker adapter.

    Args:
        session: An open :class:`~sqlalchemy.ext.asyncio.AsyncSession`
            managed by the caller.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with a database session.

        Args:
            session: The session to use for all operations within this
                request lifecycle.
        """
        self._session = session
        self._account_repo = AccountRepository(session)
        self._schwab_oauth = SchwabOAuth(session)

    async def sync_account(
        self,
        account_id: uuid.UUID,
        user_id: uuid.UUID,
        days: int = 30,
        from_date: str | None = None,
        overwrite_manually_edited: bool = False,
    ) -> BrokerSyncResult:
        """Fetch the account's broker payload and import it.

        Args:
            account_id: UUID of the account to sync.
            user_id: UUID of the authenticated user (ownership check).
            days: Number of past days to fetch (default 30). Used when
                ``from_date`` is not provided or not supported by the broker.
            from_date: Optional explicit start date in ``YYYYMMDD`` format;
                honoured by brokers that support it (IBKR Flex).
            overwrite_manually_edited: When ``True``, trades that have been
                manually edited are overwritten instead of skipped.

        Returns:
            A :class:`~app.schemas.broker.BrokerSyncResult` summarising the
            sync outcome.

        Raises:
            :class:`~app.core.exceptions.AccountNotFoundError`: If the
                account does not exist or belongs to a different user.
            :class:`~app.core.exceptions.ConfigurationError`: If the account
                type does not support API sync or required credentials are
                missing / corrupted.
            :class:`~app.core.exceptions.UpstreamServiceUnavailableError`: If
                the broker is temporarily unavailable.
        """
        account = await self._account_repo.get_by_id_with_properties(account_id, user_id)
        if account is None:
            raise AccountNotFoundError(f"Account {account_id} not found.")
        adapter = adapter_for_account_type(account.type)
        remote_sync = adapter.remote_sync if adapter is not None else None
        if adapter is None or remote_sync is None:
            raise ConfigurationError(f"Account type {AccountType(account.type).value.upper()} does not support API sync.")

        payload = await remote_sync.fetch(account, SyncWindow(days=days, from_date=from_date), self._session)

        result = await ImportService(self._session).import_trades(
            content=payload.content,
            filename=payload.filename,
            broker=adapter.key,
            portfolio_id=require_portfolio_id(account),
            account_id=account.id,
            user_id=account.user_id,
            overwrite_manually_edited=overwrite_manually_edited,
        )
        return BrokerSyncResult(
            imported_count=result.trades_created,
            skipped_count=result.trades_skipped,
            errors=[w for w in result.warnings if not w.startswith("protected_")],
            warnings=[w for w in result.warnings if w.startswith("protected_")],
            trades_protected_reconciled=result.trades_protected_reconciled,
            trades_protected_skipped=result.trades_protected_skipped,
            activity_log=result.activity_log,
        )

    async def test_connection(
        self,
        payload: BrokerConnectionTestRequest,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID,
    ) -> BrokerConnectionTestResult:
        """Validate broker credentials without persisting changes.

        Uses credentials provided in ``payload.properties`` and falls back to
        stored account properties when ``payload.account_id`` is supplied.
        """
        account: Account | None = None
        if payload.account_id is not None:
            account = await self._account_repo.get_by_id_with_properties(
                payload.account_id,
                user_id,
                portfolio_id,
            )
            if account is None:
                raise AccountNotFoundError(f"Account {payload.account_id} not found.")

        adapter = adapter_for_account_type(AccountType(payload.type))
        connection = adapter.connection if adapter is not None else None
        if connection is None:
            raise ConfigurationError(f"Account type {payload.type.upper()} does not support connection tests.")

        await connection.test(payload.properties or {}, account, self._session)
        return BrokerConnectionTestResult(success=True, message="Connection successful.")

    async def start_schwab_authorization(self, account_id: uuid.UUID, user_id: uuid.UUID) -> str:
        """Start Schwab OAuth and return the authorization URL."""
        return await self._schwab_oauth.start_authorization(account_id, user_id)

    async def complete_schwab_connection(
        self,
        account_id: uuid.UUID,
        user_id: uuid.UUID,
        redirect_url: str,
    ) -> None:
        """Complete Schwab OAuth from a pasted redirect URL (paste mode)."""
        await self._schwab_oauth.complete_connection(account_id, user_id, redirect_url)

    async def complete_schwab_callback(self, code: str, state: str) -> Account:
        """Complete Schwab OAuth from the registered callback (callback mode)."""
        return await self._schwab_oauth.complete_callback(code, state)

    async def get_schwab_status(self, account_id: uuid.UUID, user_id: uuid.UUID) -> BrokerStatusResponse:
        """Return whether the Schwab account has stored OAuth tokens."""
        return await self._schwab_oauth.get_status(account_id, user_id)

    async def disconnect_schwab(self, account_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Delete stored Schwab OAuth tokens for the account."""
        await self._schwab_oauth.disconnect(account_id, user_id)
