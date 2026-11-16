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

"""Schwab OAuth: PKCE authorization, token exchange/refresh and token storage.

Tokens are stored as encrypted account properties. The callback URL is
Schwab-registered, so these operations stay Schwab-specific and are exposed
by :class:`~app.services.broker_service.BrokerService` as thin delegations.

Audit ``path`` values (``broker_service.*``) are stable identifiers kept from
before these operations moved here.
"""

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
from app.core.exceptions import AccountNotFoundError, ConfigurationError
from app.models.account import Account
from app.repositories.account_repository import AccountRepository
from app.schemas.broker import BrokerStatusResponse
from app.services.audit_service import AuditEventService, generate_request_id
from app.services.brokers.credentials import get_property, resolve_optional_property, resolve_property
from app.utils.encryption import encrypt_token
from app.utils.oauth import (
    generate_oauth_state,
    generate_pkce_challenge,
    generate_pkce_verifier,
    validate_schwab_oauth_mode_redirect,
)
from app.utils.schwab_client import SchwabClient

logger = logging.getLogger(__name__)

SCHWAB_APP_KEY_KEYS = ("schwab_app_key", "SCHWAB_APP_KEY")
SCHWAB_APP_SECRET_KEYS = ("schwab_app_secret", "SCHWAB_APP_SECRET")
SCHWAB_ACCESS_TOKEN_KEYS = ("schwab_access_token", SCHWAB_ACCESS_TOKEN)
SCHWAB_REFRESH_TOKEN_KEYS = ("schwab_refresh_token", SCHWAB_REFRESH_TOKEN)
SCHWAB_TOKEN_EXPIRES_AT_KEYS = ("schwab_token_expires_at", SCHWAB_TOKEN_EXPIRES_AT)
SCHWAB_REFRESH_SKEW_SECONDS = 60


class SchwabOAuth:
    """Schwab OAuth operations bound to one database session.

    Args:
        session: The session used for account and property access.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with the session used for account and property access."""
        self._session = session
        self._account_repo = AccountRepository(session)
        self._audit = AuditEventService()

    async def get_valid_access_token(self, account: Account) -> str:
        """Return a non-expired access token, refreshing and storing it if needed.

        Raises:
            ConfigurationError: If the account is not connected or the refresh fails.
        """
        access_token = resolve_optional_property(account, SCHWAB_ACCESS_TOKEN_KEYS)
        refresh_token = resolve_optional_property(account, SCHWAB_REFRESH_TOKEN_KEYS)
        expires_raw = resolve_optional_property(account, SCHWAB_TOKEN_EXPIRES_AT_KEYS)

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

        client_id = resolve_property({}, account, SCHWAB_APP_KEY_KEYS)
        client_secret = resolve_property({}, account, SCHWAB_APP_SECRET_KEYS)
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
            await self._upsert_token_property(
                account_id=account.id, canonical_key=SCHWAB_ACCESS_TOKEN, legacy_key=SCHWAB_ACCESS_TOKEN_KEYS[0], value=next_access_token
            )
            await self._upsert_token_property(
                account_id=account.id, canonical_key=SCHWAB_REFRESH_TOKEN, legacy_key=SCHWAB_REFRESH_TOKEN_KEYS[0], value=next_refresh_token
            )
            await self._upsert_token_property(
                account_id=account.id, canonical_key=SCHWAB_TOKEN_EXPIRES_AT, legacy_key=SCHWAB_TOKEN_EXPIRES_AT_KEYS[0], value=next_expires_at
            )
            await self._session.flush()
        return next_access_token

    async def start_authorization(self, account_id: uuid.UUID, user_id: uuid.UUID) -> str:
        """Store PKCE/state correlation records and return the authorization URL."""
        account = await self._account_repo.get_by_id_with_properties(account_id, user_id)
        if account is None:
            raise AccountNotFoundError(f"Account {account_id} not found.")

        validate_schwab_oauth_mode_redirect(settings.schwab_oauth_mode, settings.schwab_redirect_uri)

        client_id = resolve_property({}, account, SCHWAB_APP_KEY_KEYS)
        resolve_property({}, account, SCHWAB_APP_SECRET_KEYS)

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

    async def complete_connection(
        self,
        account_id: uuid.UUID,
        user_id: uuid.UUID,
        redirect_url: str,
    ) -> None:
        """Complete OAuth in paste mode from the pasted redirect URL."""
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

        expected_state = get_property(account, SCHWAB_OAUTH_STATE)
        if not secrets.compare_digest(state, expected_state):
            raise ConfigurationError("OAuth state mismatch. Please start Schwab authorization again.")
        verifier = get_property(account, SCHWAB_OAUTH_CODE_VERIFIER)
        await self._exchange_and_store(account, code=code, state=state, verifier=verifier)

    async def complete_callback(self, code: str, state: str) -> Account:
        """Complete OAuth in callback mode; commits the session."""
        if settings.schwab_oauth_mode != "callback":
            raise ConfigurationError("Schwab callback completion is only available in callback mode.")
        if not code.strip():
            raise ConfigurationError("Callback request is missing the authorization code.")
        if not state.strip():
            raise ConfigurationError("Callback request is missing the OAuth state.")

        account = await self._resolve_account_by_oauth_state(state)
        if account is None:
            raise ConfigurationError("OAuth state could not be matched or has expired.")

        expected_state = get_property(account, SCHWAB_OAUTH_STATE)
        if not secrets.compare_digest(state, expected_state):
            raise ConfigurationError("OAuth state mismatch. Please start Schwab authorization again.")
        verifier = get_property(account, SCHWAB_OAUTH_CODE_VERIFIER)
        await self._exchange_and_store(account, code=code, state=state, verifier=verifier)
        await self._session.commit()
        return account

    async def get_status(self, account_id: uuid.UUID, user_id: uuid.UUID) -> BrokerStatusResponse:
        """Report whether OAuth access and refresh tokens are stored."""
        account = await self._account_repo.get_by_id_with_properties(account_id, user_id)
        if account is None:
            raise AccountNotFoundError(f"Account {account_id} not found.")

        has_access = resolve_optional_property(account, SCHWAB_ACCESS_TOKEN_KEYS) is not None
        has_refresh = resolve_optional_property(account, SCHWAB_REFRESH_TOKEN_KEYS) is not None
        return BrokerStatusResponse(
            connected=(has_access and has_refresh),
            last_sync_at=None,
            schwab_oauth_mode=settings.schwab_oauth_mode,
        )

    async def disconnect(self, account_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Delete all stored OAuth properties and emit the disconnect audit event."""
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

    async def _exchange_and_store(
        self,
        account: Account,
        *,
        code: str,
        state: str,
        verifier: str,
    ) -> None:
        client_id = resolve_property({}, account, SCHWAB_APP_KEY_KEYS)
        client_secret = resolve_property({}, account, SCHWAB_APP_SECRET_KEYS)

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
            await self._upsert_token_property(
                account_id=account.id, canonical_key=SCHWAB_ACCESS_TOKEN, legacy_key=SCHWAB_ACCESS_TOKEN_KEYS[0], value=access_token
            )
            await self._upsert_token_property(
                account_id=account.id, canonical_key=SCHWAB_REFRESH_TOKEN, legacy_key=SCHWAB_REFRESH_TOKEN_KEYS[0], value=refresh_token
            )
            await self._upsert_token_property(
                account_id=account.id, canonical_key=SCHWAB_TOKEN_EXPIRES_AT, legacy_key=SCHWAB_TOKEN_EXPIRES_AT_KEYS[0], value=expires_at
            )
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

    async def _resolve_account_by_oauth_state(self, state: str) -> Account | None:
        candidates = await self._account_repo.list_accounts_with_property_key_unscoped(SCHWAB_OAUTH_STATE_ACCOUNT)
        for candidate in candidates:
            value = resolve_optional_property(candidate, (SCHWAB_OAUTH_STATE_ACCOUNT,))
            if value == state:
                return candidate
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

    async def _upsert_token_property(
        self,
        *,
        account_id: uuid.UUID,
        canonical_key: str,
        legacy_key: str,
        value: str,
    ) -> None:
        """Write a Schwab token property under its canonical key.

        Also deletes any stale legacy-cased duplicate for the same logical
        property. ``resolve_optional_property`` resolves keys in
        lowercase-first order, so a leftover legacy-cased row would
        otherwise permanently shadow every future OAuth exchange/refresh,
        even though the canonical key is kept up to date.
        """
        await self._upsert_account_property_encrypted(account_id=account_id, key=canonical_key, value=value)
        if legacy_key != canonical_key:
            await self._delete_account_property(account_id=account_id, key=legacy_key)
