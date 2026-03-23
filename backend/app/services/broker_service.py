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

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AccountNotFoundError, ConfigurationError
from app.models.account import Account, AccountType
from app.models.account_property import AccountProperty
from app.models.trade import Trade
from app.schemas.broker import BrokerSyncResult
from app.schemas.trade import TradeCreate
from app.utils.encryption import decrypt_token
from app.utils.schwab_client import SchwabClient
from app.utils.schwab_normalizer import SchwabOrderNormalizer

logger = logging.getLogger(__name__)


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
        result = await self._session.execute(
            select(Account)
            .options(selectinload(Account.properties))
            .where(Account.id == account_id, Account.user_id == user_id)
        )
        account = result.scalar_one_or_none()
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
        prop: AccountProperty | None = next(
            (p for p in account.properties if p.key == key), None
        )
        if prop is None:
            raise ConfigurationError(f"Missing account property: {key}")
        try:
            return decrypt_token(prop.value)
        except Exception as exc:
            raise ConfigurationError(f"Failed to decrypt property {key}.") from exc

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
        app_key = self._get_property(account, "SCHWAB_APP_KEY")
        # Validate that the secret is present even if not used directly here
        self._get_property(account, "SCHWAB_APP_SECRET")
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
        flex_token = self._get_property(account, "IBKR_FLEX_TOKEN")
        query_id = self._get_property(account, "IBKR_FLEX_QUERY_ID")

        if from_date is None:
            now = datetime.now(UTC)
            from_date = (now - timedelta(days=days)).strftime("%Y%m%d")

        from app.core.exceptions import FlexAPIError, RateLimitError
        from app.services.flex_import_service import FlexImportService

        flex_service = FlexImportService(self._session, flex_token)

        try:
            result = await flex_service.import_flex(
                query_id=query_id,
                user_id=account.user_id,
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
        existing_ids: set[str] = set()
        if candidate_ids:
            stmt = select(Trade.broker_order_id).where(
                Trade.user_id == user_id,
                Trade.broker_order_id.in_(candidate_ids),
            )
            db_result = await self._session.execute(stmt)
            existing_ids = {row[0] for row in db_result if row[0]}

        # Insert new trades
        imported_count = 0
        for trade_create in normalised:
            if (
                trade_create.broker_order_id is not None
                and trade_create.broker_order_id in existing_ids
            ):
                skipped_count += 1
                continue
            trade_create.user_id = user_id
            create_dict = trade_create.model_dump(exclude={"tag_ids"})
            self._session.add(Trade(**create_dict))
            imported_count += 1

        await self._session.flush()
        await self._session.commit()

        return BrokerSyncResult(
            imported_count=imported_count,
            skipped_count=skipped_count,
            errors=error_messages,
        )
