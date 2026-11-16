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

"""Account-scoped import authorization and strategy locking."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import AUDIT_SUCCESS_STATUS
from app.core.exceptions import AccountNotFoundError, GenericFormatValidationError, ImportNotAllowedError
from app.models.account import Account
from app.repositories.account_repository import AccountRepository
from app.services.audit_service import AuditEventService, generate_request_id
from app.services.brokers.contracts import BrokerAdapter, BrokerType
from app.services.brokers.credentials import resolve_optional_property
from app.services.brokers.registry import adapter_for_account_type
from app.utils.encryption import encrypt_token


class ImportAccountService:
    """Enforce import capabilities and serialize first-import strategy selection."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind repositories to the caller-managed transaction."""
        self._repo = AccountRepository(session)

    async def validate_file(self, account_id: uuid.UUID, portfolio_id: uuid.UUID, user_id: uuid.UUID, extension: str) -> BrokerType:
        """Authorize file import using only the registered capability."""
        account = await self._repo.get_by_id(account_id, user_id, portfolio_id)
        if account is None:
            raise AccountNotFoundError("Account not found")
        adapter = adapter_for_account_type(account.type)
        if adapter is None or adapter.file_import is None:
            raise ImportNotAllowedError(f"File import is not supported for {account.type.value} accounts")
        if extension not in adapter.file_import.accepted_extensions:
            message = adapter.file_import.rejected_extension_message(extension)
            if message is None:
                allowed = adapter.file_import.accepted_extensions
                extensions = ", ".join(f".{item}" for item in sorted(allowed))
                message = f"Account '{account.name}' ({account.type.upper()}) only accepts {extensions} files. Received: .{extension}"
            raise ImportNotAllowedError(message)
        return adapter.key

    async def lock_strategy(
        self,
        account_id: uuid.UUID | None,
        portfolio_id: uuid.UUID,
        user_id: uuid.UUID,
        adapter: BrokerAdapter,
        strategy: str,
    ) -> Account:
        """Lock the account and reject an immutable strategy mismatch before writes."""
        if account_id is None:
            raise ImportNotAllowedError("This import requires an account")
        account = await self._repo.lock_by_id(account_id, user_id, portfolio_id)
        if account is None:
            raise AccountNotFoundError("Account not found")
        if account.type != adapter.account_type:
            raise ImportNotAllowedError("File format does not match account type")
        key = adapter.policy.id_strategy_property
        recorded = resolve_optional_property(account, (key,)) if key else None
        if recorded is not None and recorded != strategy:
            raise GenericFormatValidationError(
                [
                    {
                        "row": None,
                        "field": "external_id",
                        "code": "id_strategy_mismatch",
                        "message": "Use the account's recorded ID strategy or clear all account trades first",
                    }
                ]
            )
        return account

    async def record_strategy(self, account: Account, user_id: uuid.UUID, key: str, strategy: str) -> None:
        """Set a strategy only after successful import, logging safe metadata."""
        if resolve_optional_property(account, (key,)) is not None:
            return
        await self._repo.upsert_property(account.id, user_id, key, encrypt_token(strategy))
        AuditEventService().create_audit_event(
            action="account.import_strategy_set",
            user_id=user_id,
            email=None,
            resource_type="account",
            resource_id=account.id,
            parent_resource_type="portfolio",
            parent_resource_id=account.portfolio_id,
            ip_address=None,
            user_agent=None,
            request_id=generate_request_id(),
            status_code=AUDIT_SUCCESS_STATUS,
            method="SYSTEM",
            path="import_account_service.record_strategy",
            metadata={"account_id": str(account.id), "strategy": strategy},
        )
