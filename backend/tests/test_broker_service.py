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
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AccountNotFoundError, ConfigurationError
from app.models.account import Account, AccountType
from app.models.account_property import AccountProperty
from app.schemas.imports import ImportResult
from app.services.broker_service import BrokerService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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

        with (
            patch.object(
                svc,
                "_send_request_once",
                new=AsyncMock(side_effect=error),
            ) as mock_send_once,
            pytest.raises(FlexAPIError, match="invalid query id"),
        ):
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


class TestSchwabSyncTransactions:
    """Unit tests for Schwab sync transactions path (Part 2)."""

    @pytest.mark.unit
    async def test_sync_schwab_matches_configured_account_number(self) -> None:
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        prop_key = _make_account_property("SCHWAB_APP_KEY", "encrypted-app-key")
        prop_secret = _make_account_property("SCHWAB_APP_SECRET", "encrypted-app-secret")
        account = _make_account(AccountType.SCHWAB, properties=[prop_key, prop_secret])
        account.account_number = "45302130"  # type: ignore[attr-defined]

        svc = BrokerService(mock_session)
        import_result = ImportResult(
            broker="schwab",
            filename="schwab_transactions_sync.json",
            trades_parsed=2,
            trades_created=2,
            trades_skipped=1,
            warnings=["warn-1"],
            raw_transactions_created=2,
            raw_suppressed_skipped=0,
            raw_deleted_skipped=0,
        )

        with (
            patch("app.services.broker_service.decrypt_token", side_effect=lambda x: x.replace("encrypted-", "")),
            patch.object(svc, "_get_valid_schwab_access_token", new=AsyncMock(return_value="access-token")),
            patch(
                "app.services.broker_service.SchwabClient.get_account_numbers",
                new=AsyncMock(
                    return_value=[{"accountNumber": "45302130", "hashValue": "hash-1"}]
                ),
            ),
            patch("app.services.broker_service.SchwabClient.get_transactions", new=AsyncMock(return_value=[{"activityId": "1"}])),
            patch("app.services.broker_service.ImportService.import_file", new=AsyncMock(return_value=import_result)) as mock_import,
        ):
            result = await svc._sync_schwab(account, days=30)

        assert result.imported_count == 2
        assert result.skipped_count == 1
        assert result.errors == ["warn-1"]
        assert mock_import.await_count == 1

    @pytest.mark.unit
    async def test_sync_schwab_imports_all_transactions_from_merged_pages(self) -> None:
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        prop_key = _make_account_property("SCHWAB_APP_KEY", "encrypted-app-key")
        prop_secret = _make_account_property("SCHWAB_APP_SECRET", "encrypted-app-secret")
        account = _make_account(AccountType.SCHWAB, properties=[prop_key, prop_secret])
        account.account_number = "45302130"  # type: ignore[attr-defined]

        svc = BrokerService(mock_session)
        import_result = ImportResult(
            broker="schwab",
            filename="schwab_transactions_sync.json",
            trades_parsed=2,
            trades_created=2,
            trades_skipped=0,
            warnings=[],
            raw_transactions_created=2,
            raw_suppressed_skipped=0,
            raw_deleted_skipped=0,
        )

        merged_transactions = [
            {"activityId": 1, "type": "TRADE", "status": "VALID", "transferItems": []},
            {"activityId": 2, "type": "TRADE", "status": "VALID", "transferItems": []},
        ]

        with (
            patch("app.services.broker_service.decrypt_token", side_effect=lambda x: x.replace("encrypted-", "")),
            patch.object(svc, "_get_valid_schwab_access_token", new=AsyncMock(return_value="access-token")),
            patch(
                "app.services.broker_service.SchwabClient.get_account_numbers",
                new=AsyncMock(return_value=[{"accountNumber": "45302130", "hashValue": "hash-1"}]),
            ),
            patch(
                "app.services.broker_service.SchwabClient.get_transactions",
                new=AsyncMock(return_value=merged_transactions),
            ),
            patch("app.services.broker_service.ImportService.import_file", new=AsyncMock(return_value=import_result)) as mock_import,
        ):
            await svc._sync_schwab(account, days=30)

        call_kwargs = mock_import.await_args.kwargs
        payload = call_kwargs["content"].decode("utf-8")
        assert "\"activityId\": 1" in payload
        assert "\"activityId\": 2" in payload

    @pytest.mark.unit
    async def test_sync_schwab_single_account_auto_binds_and_audits(self) -> None:
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        prop_key = _make_account_property("SCHWAB_APP_KEY", "encrypted-app-key")
        prop_secret = _make_account_property("SCHWAB_APP_SECRET", "encrypted-app-secret")
        account = _make_account(AccountType.SCHWAB, properties=[prop_key, prop_secret])
        account.account_number = None  # type: ignore[attr-defined]

        svc = BrokerService(mock_session)
        import_result = ImportResult(
            broker="schwab",
            filename="schwab_transactions_sync.json",
            trades_parsed=0,
            trades_created=0,
            trades_skipped=0,
            warnings=[],
            raw_transactions_created=0,
            raw_suppressed_skipped=0,
            raw_deleted_skipped=0,
        )

        with (
            patch("app.services.broker_service.decrypt_token", side_effect=lambda x: x.replace("encrypted-", "")),
            patch.object(svc, "_get_valid_schwab_access_token", new=AsyncMock(return_value="access-token")),
            patch(
                "app.services.broker_service.SchwabClient.get_account_numbers",
                new=AsyncMock(
                    return_value=[{"accountNumber": "99887766", "hashValue": "hash-2"}]
                ),
            ),
            patch("app.services.broker_service.SchwabClient.get_transactions", new=AsyncMock(return_value=[])),
            patch("app.services.broker_service.ImportService.import_file", new=AsyncMock(return_value=import_result)),
            patch.object(svc, "_emit_account_number_bound_audit") as mock_audit,
        ):
            await svc._sync_schwab(account, days=1)

        assert account.account_number == "99887766"  # type: ignore[attr-defined]
        mock_session.add.assert_called_once_with(account)
        mock_session.flush.assert_awaited_once()
        mock_audit.assert_called_once()

    @pytest.mark.unit
    async def test_sync_schwab_multiple_accounts_without_config_raises(self) -> None:
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        prop_key = _make_account_property("SCHWAB_APP_KEY", "encrypted-app-key")
        prop_secret = _make_account_property("SCHWAB_APP_SECRET", "encrypted-app-secret")
        account = _make_account(AccountType.SCHWAB, properties=[prop_key, prop_secret])
        account.account_number = None  # type: ignore[attr-defined]

        svc = BrokerService(mock_session)

        with (
            patch("app.services.broker_service.decrypt_token", side_effect=lambda x: x.replace("encrypted-", "")),
            patch.object(svc, "_get_valid_schwab_access_token", new=AsyncMock(return_value="access-token")),
            patch(
                "app.services.broker_service.SchwabClient.get_account_numbers",
                new=AsyncMock(
                    return_value=[
                        {"accountNumber": "45302130", "hashValue": "hash-1"},
                        {"accountNumber": "99887766", "hashValue": "hash-2"},
                    ]
                ),
            ),
            pytest.raises(ConfigurationError, match="multiple Schwab accounts found"),
        ):
            await svc._sync_schwab(account, days=7)

    @pytest.mark.unit
    async def test_test_schwab_uses_account_numbers_probe(self) -> None:
        mock_session = AsyncMock()
        svc = BrokerService(mock_session)
        token_prop = _make_account_property("SCHWAB_ACCESS_TOKEN", "encrypted-access")
        refresh_prop = _make_account_property("SCHWAB_REFRESH_TOKEN", "encrypted-refresh")
        account = _make_account(AccountType.SCHWAB, properties=[token_prop, refresh_prop])

        with (
            patch("app.services.broker_service.decrypt_token", side_effect=lambda x: x.replace("encrypted-", "")),
            patch("app.services.broker_service.SchwabClient.get_account_numbers", new=AsyncMock(return_value=[])) as mock_probe,
            patch.object(svc, "_get_valid_schwab_access_token", new=AsyncMock(return_value="oauth-token")),
        ):
            await svc._test_schwab({}, account)

        mock_probe.assert_awaited_once_with(access_token="oauth-token")

    @pytest.mark.unit
    async def test_test_schwab_not_connected_raises(self) -> None:
        mock_session = AsyncMock()
        svc = BrokerService(mock_session)
        account = _make_account(AccountType.SCHWAB, properties=[])

        with patch("app.services.broker_service.SchwabClient.get_account_numbers", new=AsyncMock()) as mock_probe:
            with pytest.raises(ConfigurationError, match="not connected via OAuth"):
                await svc._test_schwab({}, account)

        mock_probe.assert_not_awaited()

    @pytest.mark.unit
    async def test_sync_schwab_not_connected_raises(self) -> None:
        mock_session = AsyncMock()
        svc = BrokerService(mock_session)
        account = _make_account(AccountType.SCHWAB, properties=[])

        with patch("app.services.broker_service.SchwabClient.get_transactions", new=AsyncMock()) as mock_transactions:
            with pytest.raises(ConfigurationError, match="not connected via OAuth"):
                await svc._sync_schwab(account, days=30)

        mock_transactions.assert_not_awaited()


# ---------------------------------------------------------------------------
# Tests: Schwab OAuth Connect (Tasks 6.1 - 6.4)
# ---------------------------------------------------------------------------

class TestSchwabAccessToken:
    """Unit tests for _get_valid_schwab_access_token (6.1)."""

    @pytest.mark.unit
    async def test_get_valid_token_passthrough(self) -> None:
        mock_session = AsyncMock()
        svc = BrokerService(mock_session)
        now = datetime.now(UTC)
        future = (now + timedelta(minutes=10)).isoformat()
        
        prop_access = _make_account_property("SCHWAB_ACCESS_TOKEN", "encrypted-valid-token")
        prop_refresh = _make_account_property("SCHWAB_REFRESH_TOKEN", "encrypted-refresh")
        prop_expires = _make_account_property("SCHWAB_TOKEN_EXPIRES_AT", f"encrypted-{future}")
        account = _make_account(AccountType.SCHWAB, properties=[prop_access, prop_refresh, prop_expires])

        with patch("app.services.broker_service.decrypt_token", side_effect=lambda x: x.replace("encrypted-", "")):
            token = await svc._get_valid_schwab_access_token(account)
        
        assert token == "valid-token"

    @pytest.mark.unit
    async def test_get_valid_token_refresh_on_expiry(self) -> None:
        mock_session = AsyncMock()
        mock_session.begin_nested = MagicMock()
        mock_session.begin_nested.return_value.__aenter__ = AsyncMock()
        mock_session.begin_nested.return_value.__aexit__ = AsyncMock()
        svc = BrokerService(mock_session)
        now = datetime.now(UTC)
        past = (now - timedelta(minutes=10)).isoformat()
        
        prop_access = _make_account_property("SCHWAB_ACCESS_TOKEN", "encrypted-old-token")
        prop_refresh = _make_account_property("SCHWAB_REFRESH_TOKEN", "encrypted-old-refresh")
        prop_expires = _make_account_property("SCHWAB_TOKEN_EXPIRES_AT", f"encrypted-{past}")
        prop_app_key = _make_account_property("SCHWAB_APP_KEY", "encrypted-key")
        prop_app_secret = _make_account_property("SCHWAB_APP_SECRET", "encrypted-secret")
        account = _make_account(AccountType.SCHWAB, properties=[prop_access, prop_refresh, prop_expires, prop_app_key, prop_app_secret])
        account.id = uuid.uuid4()
        
        mock_session.flush = AsyncMock()
        svc._account_repo = AsyncMock()
        svc._account_repo.get_by_id_with_properties.return_value = account

        with (
            patch("app.services.broker_service.decrypt_token", side_effect=lambda x: x.replace("encrypted-", "")),
            patch("app.services.broker_service.SchwabClient.refresh_access_token", new=AsyncMock(return_value={
                "access_token": "new-token",
                "refresh_token": "new-refresh",
                "expires_in": 1800
            })) as mock_refresh,
            patch.object(svc, "_upsert_account_property_encrypted") as mock_upsert
        ):
            token = await svc._get_valid_schwab_access_token(account)
        
        assert token == "new-token"
        mock_refresh.assert_awaited_once()
        assert mock_upsert.await_count == 3  # access, refresh, expires_at

    @pytest.mark.unit
    async def test_get_valid_token_refresh_failure(self) -> None:
        mock_session = AsyncMock()
        svc = BrokerService(mock_session)
        now = datetime.now(UTC)
        past = (now - timedelta(minutes=10)).isoformat()
        
        prop_access = _make_account_property("SCHWAB_ACCESS_TOKEN", "encrypted-old-token")
        prop_access = _make_account_property("SCHWAB_ACCESS_TOKEN", "encrypted-old-token")
        prop_refresh = _make_account_property("SCHWAB_REFRESH_TOKEN", "encrypted-old-refresh")
        prop_expires = _make_account_property("SCHWAB_TOKEN_EXPIRES_AT", f"encrypted-{past}")
        prop_app_key = _make_account_property("SCHWAB_APP_KEY", "encrypted-key")
        prop_app_secret = _make_account_property("SCHWAB_APP_SECRET", "encrypted-secret")
        account = _make_account(AccountType.SCHWAB, properties=[prop_access, prop_refresh, prop_expires, prop_app_key, prop_app_secret])

        import httpx
        err = httpx.HTTPStatusError("error", request=MagicMock(), response=MagicMock(text="invalid_grant"))

        with (
            patch("app.services.broker_service.decrypt_token", side_effect=lambda x: x.replace("encrypted-", "")),
            patch("app.services.broker_service.SchwabClient.refresh_access_token", new=AsyncMock(side_effect=err)),
            pytest.raises(ConfigurationError, match="Reconnect required via Schwab OAuth")
        ):
            await svc._get_valid_schwab_access_token(account)

class TestSchwabAuthorizeAndComplete:
    """Unit/service tests for authorize and paste-complete (6.2)."""

    @pytest.mark.unit
    async def test_start_schwab_authorization(self) -> None:
        mock_session = AsyncMock()
        svc = BrokerService(mock_session)
        account = _make_account(AccountType.SCHWAB, properties=[
            _make_account_property("SCHWAB_APP_KEY", "encrypted-key"),
            _make_account_property("SCHWAB_APP_SECRET", "encrypted-secret")
        ])
        svc._account_repo = AsyncMock()
        svc._account_repo.get_by_id_with_properties.return_value = account
        
        with (
            patch("app.services.broker_service.settings") as mock_settings,
            patch("app.services.broker_service.decrypt_token", side_effect=lambda x: x.replace("encrypted-", "")),
            patch("app.services.broker_service.generate_pkce_verifier", return_value="verifier"),
            patch("app.services.broker_service.generate_pkce_challenge", return_value="challenge"),
            patch("app.services.broker_service.generate_oauth_state", return_value="state"),
            patch("app.services.broker_service.SchwabClient.get_authorization_url", return_value="https://auth-url"),
            patch.object(svc, "_upsert_account_property_encrypted") as mock_upsert
        ):
            mock_settings.schwab_oauth_mode = "paste"
            mock_settings.schwab_redirect_uri = "https://127.0.0.1"
            url = await svc.start_schwab_authorization(account.id, account.user_id)
        
        assert url == "https://auth-url"
        assert mock_upsert.await_count == 3  # verifier, state, state_account

    @pytest.mark.unit
    async def test_complete_schwab_connection_paste_mode(self) -> None:
        mock_session = AsyncMock()
        svc = BrokerService(mock_session)
        account = _make_account(AccountType.SCHWAB, properties=[
            _make_account_property("SCHWAB_APP_KEY", "encrypted-key"),
            _make_account_property("SCHWAB_APP_SECRET", "encrypted-secret"),
            _make_account_property("SCHWAB_OAUTH_STATE", "encrypted-expected-state"),
            _make_account_property("SCHWAB_OAUTH_CODE_VERIFIER", "encrypted-verifier")
        ])
        svc._account_repo = AsyncMock()
        svc._account_repo.get_by_id_with_properties.return_value = account
        
        with (
            patch("app.services.broker_service.settings") as mock_settings,
            patch("app.services.broker_service.decrypt_token", side_effect=lambda x: x.replace("encrypted-", "")),
            patch.object(svc, "_exchange_and_store", new=AsyncMock()) as mock_exchange
        ):
            mock_settings.schwab_oauth_mode = "paste"
            await svc.complete_schwab_connection(account.id, account.user_id, "https://127.0.0.1?code=abc&state=expected-state")
        
        mock_exchange.assert_awaited_once_with(account, code="abc", state="expected-state", verifier="verifier")

    @pytest.mark.unit
    async def test_complete_schwab_connection_missing_code_or_state_mismatch(self) -> None:
        mock_session = AsyncMock()
        svc = BrokerService(mock_session)
        account = _make_account(AccountType.SCHWAB, properties=[
            _make_account_property("SCHWAB_OAUTH_STATE", "encrypted-expected-state"),
        ])
        svc._account_repo = AsyncMock()
        svc._account_repo.get_by_id_with_properties.return_value = account
        
        with patch("app.services.broker_service.settings") as mock_settings:
            mock_settings.schwab_oauth_mode = "paste"
            with pytest.raises(ConfigurationError, match="missing the authorization code"):
                await svc.complete_schwab_connection(account.id, account.user_id, "https://127.0.0.1?state=expected-state")
                
            with (
                patch("app.services.broker_service.decrypt_token", side_effect=lambda x: x.replace("encrypted-", "")),
                pytest.raises(ConfigurationError, match="OAuth state mismatch")
            ):
                await svc.complete_schwab_connection(account.id, account.user_id, "https://127.0.0.1?code=abc&state=wrong-state")

    @pytest.mark.unit
    async def test_exchange_and_store_failure(self) -> None:
        mock_session = AsyncMock()
        svc = BrokerService(mock_session)
        account = _make_account(AccountType.SCHWAB, properties=[
            _make_account_property("SCHWAB_APP_KEY", "encrypted-key"),
            _make_account_property("SCHWAB_APP_SECRET", "encrypted-secret")
        ])
        
        with (
            patch("app.services.broker_service.decrypt_token", side_effect=lambda x: x.replace("encrypted-", "")),
            patch("app.services.broker_service.SchwabClient.exchange_code", new=AsyncMock(side_effect=Exception("API down"))),
            pytest.raises(ConfigurationError, match="Schwab OAuth code exchange failed")
        ):
            await svc._exchange_and_store(account, code="abc", state="state", verifier="verifier")


class TestSchwabCallbackComplete:
    """Tests for the callback path (6.3)."""

    @pytest.mark.unit
    async def test_complete_schwab_callback_success(self) -> None:
        mock_session = AsyncMock()
        svc = BrokerService(mock_session)
        account = _make_account(AccountType.SCHWAB, properties=[
            _make_account_property("SCHWAB_OAUTH_STATE_ACCOUNT", "encrypted-state123"),
            _make_account_property("SCHWAB_OAUTH_STATE", "encrypted-state123"),
            _make_account_property("SCHWAB_OAUTH_CODE_VERIFIER", "encrypted-verifier")
        ])
        
        with (
            patch("app.services.broker_service.settings") as mock_settings,
            patch("app.services.broker_service.decrypt_token", side_effect=lambda x: x.replace("encrypted-", "")),
            patch.object(svc, "_resolve_account_by_oauth_state", new=AsyncMock(return_value=account)),
            patch.object(svc, "_exchange_and_store", new=AsyncMock()) as mock_exchange
        ):
            mock_settings.schwab_oauth_mode = "callback"
            res = await svc.complete_schwab_callback(code="code123", state="state123")
        
        assert res == account
        mock_exchange.assert_awaited_once_with(account, code="code123", state="state123", verifier="verifier")

    @pytest.mark.unit
    async def test_complete_schwab_callback_unknown_state(self) -> None:
        mock_session = AsyncMock()
        svc = BrokerService(mock_session)
        with (
            patch("app.services.broker_service.settings") as mock_settings,
            patch.object(svc, "_resolve_account_by_oauth_state", new=AsyncMock(return_value=None)),
            pytest.raises(ConfigurationError, match="could not be matched")
        ):
            mock_settings.schwab_oauth_mode = "callback"
            await svc.complete_schwab_callback(code="code123", state="unknown")


class TestSchwabStatusAndDisconnect:
    """Service tests for status and disconnect (6.4)."""

    @pytest.mark.unit
    async def test_get_schwab_status(self) -> None:
        mock_session = AsyncMock()
        svc = BrokerService(mock_session)
        account_connected = _make_account(AccountType.SCHWAB, properties=[
            _make_account_property("SCHWAB_ACCESS_TOKEN", "encrypted-acc"),
            _make_account_property("SCHWAB_REFRESH_TOKEN", "encrypted-ref"),
        ])
        svc._account_repo = AsyncMock()
        svc._account_repo.get_by_id_with_properties.return_value = account_connected
        
        with patch("app.services.broker_service.decrypt_token", side_effect=lambda x: x):
            status = await svc.get_schwab_status(account_connected.id, account_connected.user_id)
            assert status.connected is True
            
        account_disconnected = _make_account(AccountType.SCHWAB, properties=[])
        svc._account_repo.get_by_id_with_properties.return_value = account_disconnected
        status2 = await svc.get_schwab_status(account_disconnected.id, account_disconnected.user_id)
        assert status2.connected is False

    @pytest.mark.unit
    async def test_disconnect_schwab(self) -> None:
        mock_session = AsyncMock()
        svc = BrokerService(mock_session)
        account = _make_account(AccountType.SCHWAB)
        svc._account_repo = AsyncMock()
        svc._account_repo.get_by_id_with_properties.return_value = account
        
        with (
            patch.object(svc, "_delete_account_property", new=AsyncMock()) as mock_delete,
            patch.object(svc._audit, "create_audit_event") as mock_audit
        ):
            await svc.disconnect_schwab(account.id, account.user_id)
        
        assert mock_delete.await_count == 6  # access, refresh, expires, verifier, state, state_account
        mock_audit.assert_called_once()
