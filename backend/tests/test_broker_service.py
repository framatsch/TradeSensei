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

"""Unit tests for BrokerService — all DB and HTTP calls are mocked.

Tests cover the account-centric sync dispatch, property decryption error
handling, trade deduplication logic, normalisation skipping, and error
recording.  No real database or HTTP connections are made.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AccountNotFoundError, ConfigurationError
from app.models.account import Account, AccountType
from app.models.account_property import AccountProperty
from app.models.trade import AssetClass, Direction
from app.schemas.broker import BrokerSyncResult
from app.schemas.trade import TradeCreate
from app.services.broker_service import BrokerService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_trade_create(broker_order_id: str | None = "ord-1") -> TradeCreate:
    """Build a minimal :class:`TradeCreate` for test fixtures.

    Args:
        broker_order_id: The broker order identifier. Defaults to ``"ord-1"``.

    Returns:
        A :class:`TradeCreate` with sensible defaults.
    """
    now = datetime.now(tz=UTC)
    return TradeCreate(
        symbol="AAPL",
        direction=Direction.LONG,
        asset_class=AssetClass.EQUITY,
        quantity=Decimal("10"),
        entry_price=Decimal("150"),
        exit_price=Decimal("150"),
        opened_at=now,
        closed_at=now,
        currency="USD",
        broker_order_id=broker_order_id,
    )


def _make_account_property(key: str, value: str = "encrypted-value") -> AccountProperty:
    """Build a detached :class:`AccountProperty` ORM instance for testing.

    Args:
        key: Property key string (e.g. ``"SCHWAB_APP_KEY"``).
        value: Encrypted value string. Defaults to ``"encrypted-value"``.

    Returns:
        A :class:`AccountProperty` with the given key/value.
    """
    prop = AccountProperty()
    prop.id = uuid.uuid4()  # type: ignore[assignment]
    prop.account_id = uuid.uuid4()  # type: ignore[assignment]
    prop.key = key  # type: ignore[assignment]
    prop.value = value  # type: ignore[assignment]
    return prop


def _make_account(
    account_type: AccountType = AccountType.SCHWAB,
    properties: list[AccountProperty] | None = None,
) -> Account:
    """Build a detached :class:`Account` ORM instance for testing.

    Args:
        account_type: The account broker type. Defaults to ``SCHWAB``.
        properties: List of :class:`AccountProperty` instances to attach.

    Returns:
        An :class:`Account` with the given type and properties.
    """
    account = Account()
    account.id = uuid.uuid4()  # type: ignore[assignment]
    account.user_id = uuid.uuid4()  # type: ignore[assignment]
    account.portfolio_id = uuid.uuid4()  # type: ignore[assignment]
    account.name = "Test Account"  # type: ignore[assignment]
    account.type = account_type  # type: ignore[assignment]
    account.currency = "USD"  # type: ignore[assignment]
    account.is_active = True  # type: ignore[assignment]
    account.properties = properties or []  # type: ignore[assignment]
    return account


# ---------------------------------------------------------------------------
# Tests: sync_account — routing / not found
# ---------------------------------------------------------------------------


class TestSyncAccountRouting:
    """Unit tests for :meth:`BrokerService.sync_account` dispatch logic."""

    @pytest.mark.unit
    async def test_sync_account_not_found_raises(self) -> None:
        """sync_account() raises AccountNotFoundError when the account is missing.

        When the DB returns no account, the service must raise rather than
        silently returning an empty result.
        """
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        svc = BrokerService(mock_session)
        with pytest.raises(AccountNotFoundError):
            await svc.sync_account(uuid.uuid4(), uuid.uuid4())

    @pytest.mark.unit
    async def test_sync_account_manual_raises_configuration_error(self) -> None:
        """sync_account() raises ConfigurationError for MANUAL accounts.

        A MANUAL account has no API integration, so sync must always fail
        with a clear error message.
        """
        mock_session = AsyncMock()
        account = _make_account(AccountType.MANUAL)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = account
        mock_session.execute = AsyncMock(return_value=mock_result)

        svc = BrokerService(mock_session)
        with pytest.raises(ConfigurationError, match="MANUAL"):
            await svc.sync_account(account.id, account.user_id)  # type: ignore[arg-type]

    @pytest.mark.unit
    @patch("app.services.flex_import_service.FlexImportService")
    @patch("app.services.broker_service.decrypt_token")
    @patch("app.services.broker_service.datetime")
    async def test_sync_account_ibkr_success(
        self,
        mock_datetime: MagicMock,
        mock_decrypt: MagicMock,
        mock_flex_cls: MagicMock,
    ) -> None:
        """sync_account() calls FlexImportService for IBKR accounts."""
        from datetime import UTC, datetime, timedelta

        from app.schemas.imports import ImportResult

        fixed_now = datetime(2026, 3, 21, tzinfo=UTC)
        mock_datetime.now.return_value = fixed_now
        mock_datetime.side_effect = lambda *args, **kw: datetime(
            *args, **kw
        )  # fallback

        mock_decrypt.side_effect = lambda x: x.replace("encrypted-", "")

        mock_session = AsyncMock()
        prop1 = _make_account_property("ibkr_flex_token", "encrypted-test-token")
        prop2 = _make_account_property("ibkr_flex_query_id", "encrypted-12345")
        account = _make_account(AccountType.IBKR, properties=[prop1, prop2])

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = account
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_flex_instance = AsyncMock()
        mock_flex_instance.import_flex.return_value = ImportResult(
            broker="ibkr",
            filename="flex_query",
            trades_parsed=2,
            trades_created=2,
            trades_skipped=0,
            warnings=[],
        )
        mock_flex_cls.return_value = mock_flex_instance

        svc = BrokerService(mock_session)
        result = await svc.sync_account(account.id, account.user_id)  # type: ignore[arg-type]

        mock_flex_cls.assert_called_once_with(mock_session, "test-token")
        expected_from_date = (fixed_now - timedelta(days=30)).strftime("%Y%m%d")
        mock_flex_instance.import_flex.assert_called_once_with(
            query_id="12345",
            user_id=account.user_id,
            portfolio_id=account.portfolio_id,
            account_id=account.id,
            from_date=expected_from_date,
            overwrite_manually_edited=False,
        )
        assert result.imported_count == 2


class TestConnectionValidation:
    """Unit tests for BrokerService.test_connection."""

    @pytest.mark.unit
    async def test_test_connection_ibkr_uses_provided_properties(self) -> None:
        """Provided IBKR credentials should be used without DB account lookup."""
        mock_session = AsyncMock()
        svc = BrokerService(mock_session)

        request = MagicMock()
        request.type = "ibkr"
        request.properties = {
            "ibkr_flex_token": "token-1",
            "ibkr_flex_query_id": "query-1",
        }
        request.account_id = None

        with patch("app.services.flex_import_service.FlexImportService") as mock_flex_cls:
            mock_flex_instance = MagicMock()
            mock_flex_instance._fetch_flex_xml = AsyncMock(return_value="<xml/>")
            mock_flex_cls.return_value = mock_flex_instance

            result = await svc.test_connection(request, uuid.uuid4(), uuid.uuid4())

        assert result.success is True
        mock_flex_cls.assert_called_once_with(mock_session, "token-1")
        mock_flex_instance._fetch_flex_xml.assert_awaited_once_with(
            query_id="query-1",
            from_date=None,
        )


class TestFlexSendRequestFallback:
    """Unit tests for Flex send-request fallback behavior."""

    @pytest.mark.unit
    async def test_send_request_keeps_period_and_raises_on_non_transient_error(self) -> None:
        """Non-transient SendRequest errors should be raised without period fallback."""
        from app.core.exceptions import FlexAPIError
        from app.services.flex_import_service import FlexImportService

        mock_session = AsyncMock()
        svc = FlexImportService(mock_session, "token-1")

        mock_client = AsyncMock()
        error = FlexAPIError("invalid query id")

        with patch.object(
            svc,
            "_send_request_once",
            new=AsyncMock(side_effect=error),
        ) as mock_send_once:
            with pytest.raises(FlexAPIError, match="invalid query id"):
                await svc._send_request(
                    client=mock_client,
                    query_id="query-1",
                    from_date="20260601",
                )

        assert mock_send_once.await_count == 1
        first_call = mock_send_once.await_args_list[0].kwargs
        assert first_call["params"] == {
            "t": "token-1",
            "q": "query-1",
            "v": "3",
            "period": "20260601",
        }

    @pytest.mark.unit
    async def test_send_request_retries_transient_generation_error(self) -> None:
        """Transient IBKR generation errors should be retried with backoff."""
        from app.core.exceptions import FlexAPIError
        from app.services.flex_import_service import FlexImportService

        mock_session = AsyncMock()
        svc = FlexImportService(mock_session, "token-1")

        mock_client = AsyncMock()
        expected_reference = "ref-456"

        with (
            patch.object(
                svc,
                "_send_request_once",
                new=AsyncMock(
                    side_effect=[
                        FlexAPIError("Flex SendRequest failed: Statement could not be generated at this time. Please try again shortly."),
                        expected_reference,
                    ]
                ),
            ) as mock_send_once,
            patch("app.services.flex_import_service.asyncio.sleep", new=AsyncMock()) as mock_sleep,
        ):
            reference = await svc._send_request_with_retries(
                client=mock_client,
                url="https://example.test/send-request",
                params={"t": "token-1", "q": "query-1", "v": "3"},
            )

        assert reference == expected_reference
        assert mock_send_once.await_count == 2
        mock_sleep.assert_awaited_once_with(2)


# ---------------------------------------------------------------------------
# Tests: _get_property
# ---------------------------------------------------------------------------


class TestGetProperty:
    """Unit tests for :meth:`BrokerService._get_property`."""

    @pytest.mark.unit
    async def test_get_property_missing_raises(self) -> None:
        """_get_property() raises ConfigurationError for a missing key.

        When the account has no property with the requested key, the service
        must raise a descriptive :class:`ConfigurationError`.
        """
        mock_session = AsyncMock()
        account = _make_account(properties=[])

        svc = BrokerService(mock_session)
        with pytest.raises(ConfigurationError, match="SCHWAB_APP_KEY"):
            svc._get_property(account, "SCHWAB_APP_KEY")  # type: ignore[arg-type]

    @pytest.mark.unit
    async def test_get_property_decrypt_failure_raises(self) -> None:
        """_get_property() raises ConfigurationError when decryption fails.

        If the stored value cannot be decrypted (e.g. key rotation), the
        service must raise a :class:`ConfigurationError` with context.
        """
        mock_session = AsyncMock()
        prop = _make_account_property("SCHWAB_APP_KEY", "bad-ciphertext")
        account = _make_account(properties=[prop])

        svc = BrokerService(mock_session)
        with (
            patch(
                "app.services.broker_service.decrypt_token",
                side_effect=Exception("invalid token"),
            ),
            pytest.raises(ConfigurationError, match="SCHWAB_APP_KEY"),
        ):
            svc._get_property(account, "SCHWAB_APP_KEY")  # type: ignore[arg-type]

    @pytest.mark.unit
    async def test_get_property_success(self) -> None:
        """_get_property() returns the decrypted value for an existing key.

        When the property exists and decryption succeeds, the plaintext
        value must be returned.
        """
        mock_session = AsyncMock()
        prop = _make_account_property("SCHWAB_APP_KEY", "encrypted-abc")
        account = _make_account(properties=[prop])

        svc = BrokerService(mock_session)
        with patch(
            "app.services.broker_service.decrypt_token", return_value="plaintext-key"
        ):
            result = svc._get_property(account, "SCHWAB_APP_KEY")  # type: ignore[arg-type]

        assert result == "plaintext-key"


# ---------------------------------------------------------------------------
# Tests: _import_orders (via sync_account for Schwab)
# ---------------------------------------------------------------------------


class TestImportOrders:
    """Unit tests for :meth:`BrokerService._import_orders` via Schwab sync."""

    @pytest.mark.unit
    async def test_imports_new_trades(self) -> None:
        """_import_orders() imports orders not already in the database.

        Two orders are returned by the mocked client. Neither exists in the
        database, so both should be imported.
        """
        mock_session = AsyncMock()

        # DB returns no existing broker_order_ids
        mock_execute_result = MagicMock()
        mock_execute_result.__iter__ = MagicMock(return_value=iter([]))
        mock_session.execute = AsyncMock(return_value=mock_execute_result)
        mock_session.flush = AsyncMock()
        mock_session.add = MagicMock()

        svc = BrokerService(mock_session)

        trade_1 = _make_trade_create("ord-1")
        trade_2 = _make_trade_create("ord-2")

        with patch(
            "app.services.broker_service.SchwabOrderNormalizer.normalize",
            side_effect=[trade_1, trade_2],
        ):
            result: BrokerSyncResult = await svc._import_orders(
                [{"orderId": "ord-1"}, {"orderId": "ord-2"}],
                uuid.uuid4(),
            )

        assert result.imported_count == 2
        assert result.skipped_count == 0
        assert result.errors == []
        mock_session.commit.assert_called_once()

    @pytest.mark.unit
    async def test_deduplicates_existing_trades(self) -> None:
        """_import_orders() skips orders whose broker_order_id is already in the DB.

        When the database already contains a trade with the same
        broker_order_id, the sync increments skipped_count.
        """
        mock_session = AsyncMock()

        mock_execute_result = MagicMock()
        mock_execute_result.__iter__ = MagicMock(
            return_value=iter([("ord-already-exists",)])
        )
        mock_session.execute = AsyncMock(return_value=mock_execute_result)
        mock_session.flush = AsyncMock()
        mock_session.add = MagicMock()

        svc = BrokerService(mock_session)
        trade_1 = _make_trade_create("ord-already-exists")

        with patch(
            "app.services.broker_service.SchwabOrderNormalizer.normalize",
            return_value=trade_1,
        ):
            result: BrokerSyncResult = await svc._import_orders(
                [{"orderId": "ord-already-exists"}],
                uuid.uuid4(),
            )

        assert result.imported_count == 0
        assert result.skipped_count == 1

    @pytest.mark.unit
    async def test_skips_unnormalisable_orders(self) -> None:
        """_import_orders() counts skipped orders when normalize() returns None.

        Orders that the normalizer cannot process are counted as skipped
        without raising an exception.
        """
        mock_session = AsyncMock()

        mock_execute_result = MagicMock()
        mock_execute_result.__iter__ = MagicMock(return_value=iter([]))
        mock_session.execute = AsyncMock(return_value=mock_execute_result)
        mock_session.flush = AsyncMock()
        mock_session.add = MagicMock()

        svc = BrokerService(mock_session)

        with patch(
            "app.services.broker_service.SchwabOrderNormalizer.normalize",
            return_value=None,
        ):
            result: BrokerSyncResult = await svc._import_orders(
                [{"orderId": "ord-skip"}],
                uuid.uuid4(),
            )

        assert result.imported_count == 0
        assert result.skipped_count == 1

    @pytest.mark.unit
    async def test_records_normalisation_errors(self) -> None:
        """_import_orders() records errors for orders that raise during normalisation.

        If normalize() raises, the error is captured in ``errors`` and the
        sync continues with remaining orders.
        """
        mock_session = AsyncMock()

        mock_execute_result = MagicMock()
        mock_execute_result.__iter__ = MagicMock(return_value=iter([]))
        mock_session.execute = AsyncMock(return_value=mock_execute_result)
        mock_session.flush = AsyncMock()
        mock_session.add = MagicMock()

        svc = BrokerService(mock_session)

        with patch(
            "app.services.broker_service.SchwabOrderNormalizer.normalize",
            side_effect=ValueError("unexpected field"),
        ):
            result: BrokerSyncResult = await svc._import_orders(
                [{"orderId": "bad-order"}],
                uuid.uuid4(),
            )

        assert result.imported_count == 0
        assert len(result.errors) == 1
        assert "bad-order" in result.errors[0]
