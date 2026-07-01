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

import logging
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AccountNotFoundError, ConfigurationError
from app.models.account import Account, AccountType
from app.models.account_property import AccountProperty
from app.repositories.account_repository import AccountRepository
from app.repositories.trade_repository import TradeRepository
from app.schemas.broker import BrokerConnectionTestRequest, BrokerConnectionTestResult, BrokerSyncResult
from app.schemas.trade import TradeCreate
from app.utils.encryption import decrypt_token
from app.utils.schwab_client import SchwabClient
from app.utils.schwab_normalizer import SchwabOrderNormalizer

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
        self._trade_repo = TradeRepository(session)

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
        now = datetime.now(UTC)
        to_date = now.strftime("%Y-%m-%d")
        from_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        try:
            await client.get_orders(
                access_token=app_key,
                from_date=from_date,
                to_date=to_date,
            )
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
        """Fetch orders from Schwab and import new trades for the account.

        Reads ``SCHWAB_APP_KEY`` and ``SCHWAB_APP_SECRET`` from the account's
        properties, passes ``SCHWAB_APP_KEY`` as the access token to the
        :class:`~app.utils.schwab_client.SchwabClient`, and delegates order
        import to :meth:`_import_orders`.

        Args:
            account: The :class:`~app.models.account.Account` to sync.
            days: Number of past days to fetch orders for.

        Returns:
            A :class:`~app.schemas.broker.BrokerSyncResult` with import counts.
        """
        app_key = self._resolve_property({}, account, SCHWAB_APP_KEY_KEYS)
        # Validate that the secret is present even if not used directly here
        self._resolve_property({}, account, SCHWAB_APP_SECRET_KEYS)
        client = SchwabClient()
        now = datetime.now(UTC)
        to_date = now.strftime("%Y-%m-%d")
        from_date = (now - timedelta(days=days)).strftime("%Y-%m-%d")
        orders = await client.get_orders(
            access_token=app_key,
            from_date=from_date,
            to_date=to_date,
        )
        return await self._import_orders(orders, account.user_id)

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

    async def _import_orders(
        self,
        orders: Sequence[dict[str, Any]],
        user_id: uuid.UUID,
    ) -> BrokerSyncResult:
        """Normalise raw broker orders and persist new trades.

        1. Normalises each order via
           :class:`~app.utils.schwab_normalizer.SchwabOrderNormalizer`.
        2. Deduplicates by ``broker_order_id`` — skips orders already in DB.
        3. Inserts new :class:`~app.models.trade.Trade` rows.
        4. Flushes and commits the session.

        Args:
            orders: List of raw order dicts as returned by the broker API.
            user_id: UUID of the owning user for the new trades.

        Returns:
            A :class:`~app.schemas.broker.BrokerSyncResult` with counts
            of imported, skipped, and errored orders.
        """
        normalizer = SchwabOrderNormalizer()
        normalised: list[TradeCreate] = []
        error_messages: list[str] = []
        skipped_count = 0

        for order in orders:
            try:
                trade_create = normalizer.normalize(order)
                if trade_create is None:
                    skipped_count += 1
                    continue
                normalised.append(trade_create)
            except Exception as exc:
                order_id = order.get("orderId", "?")
                error_messages.append(f"Order {order_id}: {exc}")
                logger.warning("Failed to normalise order %s: %s", order_id, exc)

        # Bulk-fetch existing broker_order_ids to deduplicate
        candidate_ids = [tc.broker_order_id for tc in normalised if tc.broker_order_id]
        existing_ids = await self._trade_repo.find_by_broker_order_ids(
            user_id,
            candidate_ids,
        )

        # Insert new trades
        imported_count = 0
        new_trades: list[TradeCreate] = []
        for trade_create in normalised:
            if trade_create.broker_order_id is not None and trade_create.broker_order_id in existing_ids:
                skipped_count += 1
                continue
            trade_create.user_id = user_id
            new_trades.append(trade_create)
            imported_count += 1

        await self._trade_repo.bulk_create(new_trades)
        await self._session.commit()

        return BrokerSyncResult(
            imported_count=imported_count,
            skipped_count=skipped_count,
            errors=error_messages,
        )
