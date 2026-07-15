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

Dispatches live trade synchronisation for SCHWAB and IBKR accounts based
on the :attr:`~app.models.account.AccountType` of the account.  Broker
credentials are read from :class:`~app.models.account_property.AccountProperty`
records attached to the account and decrypted on demand.
"""

import json
import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AccountNotFoundError, ConfigurationError, ImportAccountMismatchError
from app.models.account import Account, AccountType
from app.models.account_property import AccountProperty
from app.repositories.account_repository import AccountRepository
from app.schemas.broker import BrokerConnectionTestRequest, BrokerConnectionTestResult, BrokerSyncResult
from app.services.audit_service import AuditEventService, generate_request_id
from app.services.import_service import ImportService
from app.utils.encryption import decrypt_token
from app.utils.parsers.factory import BrokerType
from app.utils.schwab_account_resolution import (
    resolve_schwab_account_entry,
)
from app.utils.schwab_client import SchwabClient

logger = logging.getLogger(__name__)

SCHWAB_APP_KEY_KEYS = ("schwab_app_key", "SCHWAB_APP_KEY")
SCHWAB_APP_SECRET_KEYS = ("schwab_app_secret", "SCHWAB_APP_SECRET")
IBKR_FLEX_TOKEN_KEYS = ("ibkr_flex_token", "IBKR_FLEX_TOKEN")
IBKR_FLEX_QUERY_ID_KEYS = ("ibkr_flex_query_id", "IBKR_FLEX_QUERY_ID")


class BrokerService:
    """Service layer for account-centric broker trade synchronisation.

    Dispatches sync operations based on the account type.  Broker
    credentials are loaded from encrypted
    :class:`~app.models.account_property.AccountProperty` records on the
    account rather than from a separate global ``broker_connections`` table.

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
        self._audit = AuditEventService()

    async def sync_account(
        self,
        account_id: uuid.UUID,
        user_id: uuid.UUID,
        days: int = 30,
        from_date: str | None = None,
        overwrite_manually_edited: bool = False,
    ) -> BrokerSyncResult:
        """Dispatch a sync for the given account based on its broker type.

        Routes to the appropriate broker-specific sync implementation
        depending on :attr:`~app.models.account.Account.type`.

        Args:
            account_id: UUID of the account to sync.
            user_id: UUID of the authenticated user (ownership check).
            days: Number of past days to fetch orders for (default 30).
                Used for Schwab and as a fallback for IBKR when
                ``from_date`` is not provided.
            from_date: Optional explicit start date in ``YYYYMMDD`` format.
                When supplied for IBKR Flex sync, this overrides the
                ``days`` calculation.
            overwrite_manually_edited: When ``True``, trades that have been
                manually edited are overwritten instead of skipped.

        Returns:
            A :class:`~app.schemas.broker.BrokerSyncResult` summarising the
            sync outcome.

        Raises:
            :class:`~app.core.exceptions.AccountNotFoundError`: If the
                account does not exist or belongs to a different user.
            :class:`~app.core.exceptions.ConfigurationError`: If the account
                type is ``MANUAL`` (no API sync supported) or required
                credentials are missing / corrupted.
        """
        account = await self._account_repo.get_by_id_with_properties(account_id, user_id)
        if account is None:
            raise AccountNotFoundError(f"Account {account_id} not found.")
        if account.type == AccountType.SCHWAB:
            return await self._sync_schwab(account, days)
        elif account.type == AccountType.IBKR:
            return await self._sync_ibkr(
                account,
                days,
                from_date=from_date,
                overwrite_manually_edited=overwrite_manually_edited,
            )
        else:
            raise ConfigurationError("Account type MANUAL does not support API sync.")

    async def test_connection(
        self,
        payload: BrokerConnectionTestRequest,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID,
    ) -> BrokerConnectionTestResult:
        """Validate broker credentials for Schwab or IBKR without persisting changes.

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

        if payload.type == AccountType.SCHWAB.value:
            await self._test_schwab(payload.properties or {}, account)
            return BrokerConnectionTestResult(success=True, message="Connection successful.")

        await self._test_ibkr(payload.properties or {}, account, user_id, portfolio_id)
        return BrokerConnectionTestResult(success=True, message="Connection successful.")

    def _get_property(self, account: Account, key: str) -> str:
        """Retrieve and decrypt a named property from the account.

        Args:
            account: The :class:`~app.models.account.Account` whose
                properties are searched.
            key: The property key to look up (e.g. ``"SCHWAB_APP_KEY"``).

        Returns:
            The decrypted plaintext value of the property.

        Raises:
            :class:`~app.core.exceptions.ConfigurationError`: If the key
                is not found among the account's properties, or if
                decryption fails.
        """
        prop: AccountProperty | None = next((p for p in account.properties if p.key == key), None)
        if prop is None:
            raise ConfigurationError(f"Missing account property: {key}")
        try:
            return decrypt_token(prop.value)
        except Exception as exc:
            raise ConfigurationError(f"Failed to decrypt property {key}.") from exc

    def _resolve_property(
        self,
        provided: dict[str, str],
        account: Account | None,
        keys: tuple[str, ...],
    ) -> str:
        for key in keys:
            value = provided.get(key)
            if value is not None and value.strip() != "":
                return value.strip()

        if account is not None:
            for key in keys:
                prop: AccountProperty | None = next(
                    (p for p in account.properties if p.key == key),
                    None,
                )
                if prop is None:
                    continue
                try:
                    return decrypt_token(prop.value)
                except Exception as exc:
                    raise ConfigurationError(f"Failed to decrypt property {key}.") from exc

        raise ConfigurationError(f"Missing account property: {keys[0]}")

    async def _test_schwab(self, provided: dict[str, str], account: Account | None) -> None:
        app_key = self._resolve_property(provided, account, SCHWAB_APP_KEY_KEYS)
        self._resolve_property(provided, account, SCHWAB_APP_SECRET_KEYS)

        client = SchwabClient()
        try:
            await client.get_account_numbers(access_token=app_key)
        except Exception as exc:
            raise ConfigurationError(f"Schwab connection test failed: {exc}") from exc

    async def _test_ibkr(
        self,
        provided: dict[str, str],
        account: Account | None,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID,
    ) -> None:
        flex_token = self._resolve_property(provided, account, IBKR_FLEX_TOKEN_KEYS)
        query_id = self._resolve_property(provided, account, IBKR_FLEX_QUERY_ID_KEYS)

        from app.services.flex_import_service import FlexImportService

        service = FlexImportService(self._session, flex_token)
        try:
            await service._fetch_flex_xml(query_id=query_id, from_date=None)
        except Exception as exc:
            raise ConfigurationError(f"IBKR connection test failed: {exc}") from exc

    async def _sync_schwab(self, account: Account, days: int) -> BrokerSyncResult:
        """Fetch Schwab transactions and import via the shared raw pipeline."""
        app_key = self._resolve_property({}, account, SCHWAB_APP_KEY_KEYS)
        self._resolve_property({}, account, SCHWAB_APP_SECRET_KEYS)

        if account.portfolio_id is None:
            raise ConfigurationError(f"Account {account.id} is not linked to a portfolio.")

        client = SchwabClient()

        account_numbers = await client.get_account_numbers(access_token=app_key)
        try:
            selected, auto_bound_number = resolve_schwab_account_entry(
                accounts=account_numbers,
                configured_account_number=account.account_number,
                context="sync",
            )
        except ImportAccountMismatchError as exc:
            raise ConfigurationError(str(exc)) from exc

        if account.account_number is None and auto_bound_number is not None:
            account.account_number = auto_bound_number
            self._session.add(account)
            await self._session.flush()
            self._emit_account_number_bound_audit(
                user_id=account.user_id,
                account_id=account.id,
                portfolio_id=account.portfolio_id,
            )

        account_hash = str(selected.get("hashValue", "")).strip()
        if not account_hash:
            raise ConfigurationError("Schwab sync failed: resolved broker account is missing hashValue.")

        now = datetime.now(UTC)
        from_date = now - timedelta(days=days)
        to_date = now
        transactions = await client.get_transactions(
            access_token=app_key,
            account_hash=account_hash,
            from_date=from_date,
            to_date=to_date,
        )

        wrapped_payload = {
            "accounts": [
                {
                    "accountNumber": str(selected.get("accountNumber", "")).strip(),
                    "transactions": transactions,
                }
            ]
        }

        import_service = ImportService(self._session)
        result = await import_service.import_file(
            content=json.dumps(wrapped_payload).encode("utf-8"),
            filename="schwab_transactions_sync.json",
            broker=BrokerType.SCHWAB,
            portfolio_id=account.portfolio_id,
            account_id=account.id,
            user_id=account.user_id,
        )
        return BrokerSyncResult(
            imported_count=result.trades_created,
            skipped_count=result.trades_skipped,
            errors=result.warnings,
        )

    def _emit_account_number_bound_audit(
        self,
        *,
        user_id: uuid.UUID,
        account_id: uuid.UUID,
        portfolio_id: uuid.UUID,
    ) -> None:
        self._audit.create_audit_event(
            action="account.account_number_bound",
            user_id=user_id,
            email=None,
            resource_type="account",
            resource_id=account_id,
            parent_resource_type="portfolio",
            parent_resource_id=portfolio_id,
            ip_address=None,
            user_agent=None,
            request_id=generate_request_id(),
            status_code=200,
            method="SYSTEM",
            path="broker_service._sync_schwab",
            metadata={
                "reason": "schwab_single_account_auto_bind",
            },
        )

    async def _sync_ibkr(
        self,
        account: Account,
        days: int,
        from_date: str | None = None,
        overwrite_manually_edited: bool = False,
    ) -> BrokerSyncResult:
        """Fetch orders via IBKR Flex Query and import new trades for the account.

        Reads ``IBKR_FLEX_TOKEN`` and ``IBKR_FLEX_QUERY_ID`` from the account's
        properties.

        Args:
            account: The :class:`~app.models.account.Account` to sync.
            days: Number of past days to fetch orders for. Used as fallback
                when ``from_date`` is not provided.
            from_date: Optional explicit start date in ``YYYYMMDD`` format.
                When provided, this overrides the ``days``-based calculation.
            overwrite_manually_edited: When ``True``, trades that have been
                manually edited are overwritten instead of skipped.

        Returns:
            A :class:`~app.schemas.broker.BrokerSyncResult` with import counts.

        Raises:
            :class:`~app.core.exceptions.ConfigurationError`: If required
                credentials are missing or if the API returns an error.
        """
        flex_token = self._resolve_property({}, account, IBKR_FLEX_TOKEN_KEYS)
        query_id = self._resolve_property({}, account, IBKR_FLEX_QUERY_ID_KEYS)

        if from_date is None:
            now = datetime.now(UTC)
            from_date = (now - timedelta(days=days)).strftime("%Y%m%d")

        from app.core.exceptions import FlexAPIError, RateLimitError
        from app.services.flex_import_service import FlexImportService

        flex_service = FlexImportService(self._session, flex_token)
        if account.portfolio_id is None:
            raise ConfigurationError(f"Account {account.id} is not linked to a portfolio.")

        try:
            result = await flex_service.import_flex(
                query_id=query_id,
                user_id=account.user_id,
                portfolio_id=account.portfolio_id,
                account_id=account.id,
                from_date=from_date,
                overwrite_manually_edited=overwrite_manually_edited,
            )
            return BrokerSyncResult(
                imported_count=result.trades_created,
                skipped_count=result.trades_skipped,
                errors=result.warnings,
            )
        except RateLimitError as exc:
            raise ConfigurationError(f"IBKR API rate limit reached: {exc}") from exc
        except FlexAPIError as exc:
            raise ConfigurationError(f"IBKR Flex API error: {exc}") from exc
