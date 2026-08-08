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
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import (
    SCHWAB_ACCESS_TOKEN,
    SCHWAB_OAUTH_CODE_VERIFIER,
    SCHWAB_OAUTH_STATE,
    SCHWAB_OAUTH_STATE_ACCOUNT,
    SCHWAB_REFRESH_TOKEN,
    SCHWAB_TOKEN_EXPIRES_AT,
)
from app.core.exceptions import AccountNotFoundError, ConfigurationError, ImportAccountMismatchError
from app.models.account import Account, AccountType
from app.models.account_property import AccountProperty
from app.repositories.account_repository import AccountRepository
from app.schemas.broker import (
    BrokerConnectionTestRequest,
    BrokerConnectionTestResult,
    BrokerStatusResponse,
    BrokerSyncResult,
)
from app.services.audit_service import AuditEventService, generate_request_id
from app.services.import_service import ImportService
from app.utils.encryption import decrypt_token, encrypt_token
from app.utils.oauth import (
    generate_oauth_state,
    generate_pkce_challenge,
    generate_pkce_verifier,
    validate_schwab_oauth_mode_redirect,
)
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
SCHWAB_ACCESS_TOKEN_KEYS = ("schwab_access_token", SCHWAB_ACCESS_TOKEN)
SCHWAB_REFRESH_TOKEN_KEYS = ("schwab_refresh_token", SCHWAB_REFRESH_TOKEN)
SCHWAB_TOKEN_EXPIRES_AT_KEYS = ("schwab_token_expires_at", SCHWAB_TOKEN_EXPIRES_AT)
SCHWAB_REFRESH_SKEW_SECONDS = 60


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
            return await self._sync_schwab(account, days, overwrite_manually_edited=overwrite_manually_edited)
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

    def _resolve_optional_property(
        self,
        account: Account,
        keys: tuple[str, ...],
    ) -> str | None:
        for key in keys:
            prop: AccountProperty | None = next((p for p in account.properties if p.key == key), None)
            if prop is None:
                continue
            try:
                return decrypt_token(prop.value)
            except Exception as exc:
                raise ConfigurationError(f"Failed to decrypt property {key}.") from exc
        return None

    async def _upsert_account_property_encrypted(
        self,
        *,
        account_id: uuid.UUID,
        key: str,
        value: str,
    ) -> None:
        await self._account_repo.upsert_property_unscoped(
            account_id=account_id,
            key=key,
            encrypted_value=encrypt_token(value),
        )

    async def _delete_account_property(
        self,
        *,
        account_id: uuid.UUID,
        key: str,
    ) -> None:
        await self._account_repo.delete_property_unscoped(account_id=account_id, key=key)

    async def _resolve_account_by_oauth_state(self, state: str) -> Account | None:
        candidates = await self._account_repo.list_accounts_with_property_key_unscoped(SCHWAB_OAUTH_STATE_ACCOUNT)
        for candidate in candidates:
            value = self._resolve_optional_property(candidate, (SCHWAB_OAUTH_STATE_ACCOUNT,))
            if value == state:
                return candidate
        return None

    async def _test_schwab(self, provided: dict[str, str], account: Account | None) -> None:
        del provided
        if account is None:
            raise ConfigurationError("Schwab account must be created before testing OAuth connectivity.")

        access_token = self._resolve_optional_property(account, SCHWAB_ACCESS_TOKEN_KEYS)
        refresh_token = self._resolve_optional_property(account, SCHWAB_REFRESH_TOKEN_KEYS)
        if not access_token or not refresh_token:
            raise ConfigurationError("Schwab account is not connected via OAuth. Please connect via OAuth first.")

        valid_token = await self._get_valid_schwab_access_token(account)
        client = SchwabClient()
        try:
            await client.get_account_numbers(access_token=valid_token)
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

    async def _get_valid_schwab_access_token(self, account: Account) -> str:
        access_token = self._resolve_optional_property(account, SCHWAB_ACCESS_TOKEN_KEYS)
        refresh_token = self._resolve_optional_property(account, SCHWAB_REFRESH_TOKEN_KEYS)
        expires_raw = self._resolve_optional_property(account, SCHWAB_TOKEN_EXPIRES_AT_KEYS)

        if not access_token or not refresh_token:
            raise ConfigurationError("Schwab account is not connected via OAuth. Please connect via OAuth first.")

        expires_at: datetime | None = None
        if expires_raw:
            raw = expires_raw.strip()
            if raw.endswith("Z"):
                raw = f"{raw[:-1]}+00:00"
            try:
                expires_at = datetime.fromisoformat(raw)
            except ValueError:
                expires_at = None

        now = datetime.now(UTC)
        if expires_at is not None and expires_at.tzinfo is not None and expires_at > now + timedelta(seconds=SCHWAB_REFRESH_SKEW_SECONDS):
            return access_token

        client_id = self._resolve_property({}, account, SCHWAB_APP_KEY_KEYS)
        client_secret = self._resolve_property({}, account, SCHWAB_APP_SECRET_KEYS)
        client = SchwabClient()
        try:
            refreshed = await client.refresh_access_token(
                refresh_token=refresh_token,
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=settings.schwab_redirect_uri,
            )
        except httpx.HTTPStatusError as exc:
            response_text = (exc.response.text if exc.response is not None else "").lower()
            if "invalid_client" in response_text or "invalid_grant" in response_text:
                raise ConfigurationError("Schwab refresh token is invalid or expired. Reconnect required via Schwab OAuth.") from exc
            raise ConfigurationError(f"Schwab access-token refresh failed: {exc}") from exc
        except Exception as exc:
            raise ConfigurationError(f"Schwab access-token refresh failed: {exc}") from exc

        next_access_token = str(refreshed.get("access_token", "")).strip()
        if not next_access_token:
            raise ConfigurationError("Schwab refresh response did not include an access_token.")
        expires_in = int(refreshed.get("expires_in", 0) or 0)
        if expires_in <= 0:
            raise ConfigurationError("Schwab refresh response did not include a valid expires_in value.")

        next_refresh_token = str(refreshed.get("refresh_token") or refresh_token).strip()
        next_expires_at = (datetime.now(UTC) + timedelta(seconds=expires_in)).isoformat()

        async with self._session.begin_nested():
            await self._upsert_account_property_encrypted(account_id=account.id, key=SCHWAB_ACCESS_TOKEN, value=next_access_token)
            await self._upsert_account_property_encrypted(account_id=account.id, key=SCHWAB_REFRESH_TOKEN, value=next_refresh_token)
            await self._upsert_account_property_encrypted(account_id=account.id, key=SCHWAB_TOKEN_EXPIRES_AT, value=next_expires_at)
            await self._session.flush()
        return next_access_token

    async def start_schwab_authorization(self, account_id: uuid.UUID, user_id: uuid.UUID) -> str:
        account = await self._account_repo.get_by_id_with_properties(account_id, user_id)
        if account is None:
            raise AccountNotFoundError(f"Account {account_id} not found.")

        validate_schwab_oauth_mode_redirect(settings.schwab_oauth_mode, settings.schwab_redirect_uri)

        client_id = self._resolve_property({}, account, SCHWAB_APP_KEY_KEYS)
        self._resolve_property({}, account, SCHWAB_APP_SECRET_KEYS)

        verifier = generate_pkce_verifier()
        challenge = generate_pkce_challenge(verifier)
        state = generate_oauth_state()

        await self._upsert_account_property_encrypted(account_id=account.id, key=SCHWAB_OAUTH_CODE_VERIFIER, value=verifier)
        await self._upsert_account_property_encrypted(account_id=account.id, key=SCHWAB_OAUTH_STATE, value=state)
        await self._upsert_account_property_encrypted(account_id=account.id, key=SCHWAB_OAUTH_STATE_ACCOUNT, value=state)
        await self._session.flush()

        client = SchwabClient()
        return client.get_authorization_url(
            state=state,
            code_challenge=challenge,
            client_id=client_id,
            redirect_uri=settings.schwab_redirect_uri,
        )

    async def _exchange_and_store(
        self,
        account: Account,
        *,
        code: str,
        state: str,
        verifier: str,
    ) -> None:
        client_id = self._resolve_property({}, account, SCHWAB_APP_KEY_KEYS)
        client_secret = self._resolve_property({}, account, SCHWAB_APP_SECRET_KEYS)

        client = SchwabClient()
        try:
            exchanged = await client.exchange_code(
                code=code,
                code_verifier=verifier,
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=settings.schwab_redirect_uri,
            )
        except httpx.HTTPStatusError as exc:
            err_body = exc.response.text
            msg = f"Schwab OAuth code exchange failed: {exc} - Response: {err_body}"
            logger.error(msg)
            raise ConfigurationError(msg) from exc
        except Exception as exc:
            msg = f"Schwab OAuth code exchange failed: {exc}"
            logger.error(msg, exc_info=True)
            raise ConfigurationError(msg) from exc
        access_token = str(exchanged.get("access_token", "")).strip()
        refresh_token = str(exchanged.get("refresh_token", "")).strip()
        expires_in = int(exchanged.get("expires_in", 0) or 0)
        if not access_token or not refresh_token or expires_in <= 0:
            raise ConfigurationError("Schwab OAuth exchange response was missing required token fields.")

        expires_at = (datetime.now(UTC) + timedelta(seconds=expires_in)).isoformat()
        async with self._session.begin_nested():
            await self._upsert_account_property_encrypted(account_id=account.id, key=SCHWAB_ACCESS_TOKEN, value=access_token)
            await self._upsert_account_property_encrypted(account_id=account.id, key=SCHWAB_REFRESH_TOKEN, value=refresh_token)
            await self._upsert_account_property_encrypted(account_id=account.id, key=SCHWAB_TOKEN_EXPIRES_AT, value=expires_at)
            await self._delete_account_property(account_id=account.id, key=SCHWAB_OAUTH_CODE_VERIFIER)
            await self._delete_account_property(account_id=account.id, key=SCHWAB_OAUTH_STATE)
            await self._delete_account_property(account_id=account.id, key=SCHWAB_OAUTH_STATE_ACCOUNT)
            await self._session.flush()

        self._audit.create_audit_event(
            action="broker.schwab_connected",
            user_id=account.user_id,
            email=None,
            resource_type="account",
            resource_id=account.id,
            parent_resource_type="portfolio",
            parent_resource_id=account.portfolio_id,
            ip_address=None,
            user_agent=None,
            request_id=generate_request_id(),
            status_code=200,
            method="SYSTEM",
            path="broker_service._exchange_and_store",
            metadata={"provider": "schwab", "state_present": bool(state)},
        )

    async def complete_schwab_connection(
        self,
        account_id: uuid.UUID,
        user_id: uuid.UUID,
        redirect_url: str,
    ) -> None:
        if settings.schwab_oauth_mode != "paste":
            raise ConfigurationError("Schwab OAuth completion via pasted URL is only available in paste mode.")

        account = await self._account_repo.get_by_id_with_properties(account_id, user_id)
        if account is None:
            raise AccountNotFoundError(f"Account {account_id} not found.")

        parsed = urlparse(redirect_url)
        query = parse_qs(parsed.query)
        code = (query.get("code") or [""])[0].strip()
        state = (query.get("state") or [""])[0].strip()
        if not code:
            raise ConfigurationError("Redirect URL is missing the authorization code.")
        if not state:
            raise ConfigurationError("Redirect URL is missing the OAuth state.")

        expected_state = self._get_property(account, SCHWAB_OAUTH_STATE)
        if not secrets.compare_digest(state, expected_state):
            raise ConfigurationError("OAuth state mismatch. Please start Schwab authorization again.")
        verifier = self._get_property(account, SCHWAB_OAUTH_CODE_VERIFIER)
        await self._exchange_and_store(account, code=code, state=state, verifier=verifier)

    async def complete_schwab_callback(self, code: str, state: str) -> Account:
        if settings.schwab_oauth_mode != "callback":
            raise ConfigurationError("Schwab callback completion is only available in callback mode.")
        if not code.strip():
            raise ConfigurationError("Callback request is missing the authorization code.")
        if not state.strip():
            raise ConfigurationError("Callback request is missing the OAuth state.")

        account = await self._resolve_account_by_oauth_state(state)
        if account is None:
            raise ConfigurationError("OAuth state could not be matched or has expired.")

        expected_state = self._get_property(account, SCHWAB_OAUTH_STATE)
        if not secrets.compare_digest(state, expected_state):
            raise ConfigurationError("OAuth state mismatch. Please start Schwab authorization again.")
        verifier = self._get_property(account, SCHWAB_OAUTH_CODE_VERIFIER)
        await self._exchange_and_store(account, code=code, state=state, verifier=verifier)
        await self._session.commit()
        return account

    async def get_schwab_status(self, account_id: uuid.UUID, user_id: uuid.UUID) -> BrokerStatusResponse:
        account = await self._account_repo.get_by_id_with_properties(account_id, user_id)
        if account is None:
            raise AccountNotFoundError(f"Account {account_id} not found.")

        has_access = self._resolve_optional_property(account, SCHWAB_ACCESS_TOKEN_KEYS) is not None
        has_refresh = self._resolve_optional_property(account, SCHWAB_REFRESH_TOKEN_KEYS) is not None
        return BrokerStatusResponse(
            connected=(has_access and has_refresh),
            last_sync_at=None,
            schwab_oauth_mode=settings.schwab_oauth_mode,
        )

    async def disconnect_schwab(self, account_id: uuid.UUID, user_id: uuid.UUID) -> None:
        account = await self._account_repo.get_by_id_with_properties(account_id, user_id)
        if account is None:
            raise AccountNotFoundError(f"Account {account_id} not found.")

        for key in SCHWAB_ACCESS_TOKEN_KEYS:
            await self._delete_account_property(account_id=account.id, key=key)
        for key in SCHWAB_REFRESH_TOKEN_KEYS:
            await self._delete_account_property(account_id=account.id, key=key)
        for key in SCHWAB_TOKEN_EXPIRES_AT_KEYS:
            await self._delete_account_property(account_id=account.id, key=key)

        await self._delete_account_property(account_id=account.id, key=SCHWAB_OAUTH_CODE_VERIFIER)
        await self._delete_account_property(account_id=account.id, key=SCHWAB_OAUTH_STATE)
        await self._delete_account_property(account_id=account.id, key=SCHWAB_OAUTH_STATE_ACCOUNT)
        await self._session.flush()

        self._audit.create_audit_event(
            action="broker.schwab_disconnected",
            user_id=account.user_id,
            email=None,
            resource_type="account",
            resource_id=account.id,
            parent_resource_type="portfolio",
            parent_resource_id=account.portfolio_id,
            ip_address=None,
            user_agent=None,
            request_id=generate_request_id(),
            status_code=200,
            method="SYSTEM",
            path="broker_service.disconnect_schwab",
            metadata={"provider": "schwab"},
        )

    async def _sync_schwab(self, account: Account, days: int, overwrite_manually_edited: bool = False) -> BrokerSyncResult:
        """Fetch Schwab transactions and import via the shared raw pipeline."""
        access_token = await self._get_valid_schwab_access_token(account)
        self._resolve_property({}, account, SCHWAB_APP_KEY_KEYS)
        self._resolve_property({}, account, SCHWAB_APP_SECRET_KEYS)

        if account.portfolio_id is None:
            raise ConfigurationError(f"Account {account.id} is not linked to a portfolio.")

        client = SchwabClient()

        account_numbers = await client.get_account_numbers(access_token=access_token)
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
            access_token=access_token,
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
                errors=[w for w in result.warnings if not w.startswith("protected_")],
                warnings=[w for w in result.warnings if w.startswith("protected_")],
                trades_protected_reconciled=result.trades_protected_reconciled,
                trades_protected_skipped=result.trades_protected_skipped,
                activity_log=result.activity_log,
            )
        except RateLimitError as exc:
            raise ConfigurationError(f"IBKR API rate limit reached: {exc}") from exc
        except FlexAPIError as exc:
            raise ConfigurationError(f"IBKR Flex API error: {exc}") from exc
