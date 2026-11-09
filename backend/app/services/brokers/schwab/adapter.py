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

"""Charles Schwab adapter: JSON import, account binding, OAuth-based sync."""

import json
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConfigurationError, ImportAccountMismatchError, ImportParseError
from app.models.account import Account, AccountType
from app.services.audit_service import AuditEventService, generate_request_id
from app.services.brokers.contracts import (
    BindingResult,
    BrokerAdapter,
    BrokerType,
    CanonicalImportBatch,
    FetchedPayload,
    ImportPolicy,
    SyncWindow,
)
from app.services.brokers.credentials import require_portfolio_id, resolve_optional_property, resolve_property
from app.services.brokers.schwab.oauth import (
    SCHWAB_ACCESS_TOKEN_KEYS,
    SCHWAB_APP_KEY_KEYS,
    SCHWAB_APP_SECRET_KEYS,
    SCHWAB_REFRESH_TOKEN_KEYS,
    SchwabOAuth,
)
from app.utils.parsers.schwab_json import SchwabJSONParser, decode_schwab_wrapped_payload
from app.utils.schwab_account_resolution import resolve_schwab_account_entry
from app.utils.schwab_client import SchwabClient


def emit_account_number_bound_audit(
    *,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
    portfolio_id: uuid.UUID | None,
    path: str,
) -> None:
    """Emit the manual audit event for an auto-bound Schwab account number.

    ``path`` values are stable audit identifiers kept from before the adapter
    refactor (``import_service.import_trades`` / ``broker_service._sync_schwab``).
    """
    AuditEventService().create_audit_event(
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
        path=path,
        metadata={
            "reason": "schwab_single_account_auto_bind",
        },
    )


class SchwabFileImport:
    """Parses the wrapped Schwab transactions JSON ``{accounts: [...]}``."""

    accepted_extensions: frozenset[str] = frozenset({"json"})

    def rejected_extension_message(self, extension: str) -> str | None:
        """Explain that the former Schwab CSV export is no longer accepted."""
        if extension == "csv":
            return "Schwab accounts require JSON format (.json). CSV import is no longer supported."
        return None

    def parse(self, content: bytes, filename: str) -> CanonicalImportBatch:
        """Parse Schwab JSON into a canonical batch; skipped rows become warnings."""
        parser = SchwabJSONParser()
        executions, corporate_actions = parser.parse_raw(content, filename)
        return CanonicalImportBatch(
            executions=executions,
            corporate_actions=corporate_actions,
            warnings=list(parser.warnings),
        )


class SchwabAccountBinding:
    """Selects the ``accounts[]`` entry for the target account.

    A payload with exactly one entry auto-binds that entry's number to an
    account without ``account_number``; a mismatch or ambiguity raises
    :class:`~app.core.exceptions.ImportAccountMismatchError`.
    """

    async def bind(self, content: bytes, account: Account, session: AsyncSession) -> BindingResult:
        """Reduce the payload to the account's entry, binding an unset number."""
        payload = decode_schwab_wrapped_payload(content)
        accounts = payload.get("accounts")
        assert isinstance(accounts, list)
        bound_account_number: str | None = None
        if accounts:
            selected_account, selected_account_number = _select_account_entry(
                payload,
                account_number=account.account_number,
            )
            if account.account_number is None and selected_account_number is not None:
                account.account_number = selected_account_number
                session.add(account)
                await session.flush()
                emit_account_number_bound_audit(
                    user_id=account.user_id,
                    account_id=account.id,
                    portfolio_id=account.portfolio_id,
                    path="import_service.import_trades",
                )
                bound_account_number = selected_account_number
            payload["accounts"] = [selected_account]
        return BindingResult(content=json.dumps(payload).encode("utf-8"), bound_account_number=bound_account_number)


def _select_account_entry(
    payload: dict[str, object],
    account_number: str | None,
) -> tuple[dict[str, object], str | None]:
    accounts_obj = payload.get("accounts")
    assert isinstance(accounts_obj, list)
    file_accounts: list[dict[str, object]] = [entry for entry in accounts_obj if isinstance(entry, dict)]
    if len(file_accounts) != len(accounts_obj):
        raise ImportParseError("Schwab JSON payload contains invalid account entries; each accounts item must be an object.")

    return resolve_schwab_account_entry(
        accounts=file_accounts,
        configured_account_number=account_number,
        context="import",
    )


class SchwabRemoteSync:
    """Fetches account transactions from the Schwab Trader API.

    Refreshes the OAuth access token when needed, resolves (and may
    auto-bind) the broker account, and wraps the transactions in the same
    ``{accounts: [...]}`` payload the file import accepts.
    """

    async def fetch(self, account: Account, window: SyncWindow, session: AsyncSession) -> FetchedPayload:
        """Fetch the last ``window.days`` days of transactions for ``account``."""
        access_token = await SchwabOAuth(session).get_valid_access_token(account)
        resolve_property({}, account, SCHWAB_APP_KEY_KEYS)
        resolve_property({}, account, SCHWAB_APP_SECRET_KEYS)
        require_portfolio_id(account)

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
            session.add(account)
            await session.flush()
            emit_account_number_bound_audit(
                user_id=account.user_id,
                account_id=account.id,
                portfolio_id=account.portfolio_id,
                path="broker_service._sync_schwab",
            )

        account_hash = str(selected.get("hashValue", "")).strip()
        if not account_hash:
            raise ConfigurationError("Schwab sync failed: resolved broker account is missing hashValue.")

        now = datetime.now(UTC)
        transactions = await client.get_transactions(
            access_token=access_token,
            account_hash=account_hash,
            from_date=now - timedelta(days=window.days),
            to_date=now,
        )

        wrapped_payload = {
            "accounts": [
                {
                    "accountNumber": str(selected.get("accountNumber", "")).strip(),
                    "transactions": transactions,
                }
            ]
        }
        return FetchedPayload(content=json.dumps(wrapped_payload).encode("utf-8"), filename="schwab_transactions_sync.json")


class SchwabConnection:
    """Validates a Schwab OAuth connection with an account-numbers probe."""

    async def test(self, provided: dict[str, str], account: Account | None, session: AsyncSession) -> None:
        """Probe the Trader API with the stored (refreshed if needed) token."""
        del provided
        if account is None:
            raise ConfigurationError("Schwab account must be created before testing OAuth connectivity.")

        access_token = resolve_optional_property(account, SCHWAB_ACCESS_TOKEN_KEYS)
        refresh_token = resolve_optional_property(account, SCHWAB_REFRESH_TOKEN_KEYS)
        if not access_token or not refresh_token:
            raise ConfigurationError("Schwab account is not connected via OAuth. Please connect via OAuth first.")

        valid_token = await SchwabOAuth(session).get_valid_access_token(account)
        client = SchwabClient()
        try:
            await client.get_account_numbers(access_token=valid_token)
        except Exception as exc:
            raise ConfigurationError(f"Schwab connection test failed: {exc}") from exc


SCHWAB_ADAPTER = BrokerAdapter(
    key=BrokerType.SCHWAB,
    account_type=AccountType.SCHWAB,
    policy=ImportPolicy(self_heal_pending_protected_close=True),
    file_import=SchwabFileImport(),
    account_binding=SchwabAccountBinding(),
    remote_sync=SchwabRemoteSync(),
    connection=SchwabConnection(),
)
