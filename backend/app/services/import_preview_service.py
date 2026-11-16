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

"""Read-only raw execution novelty preview for generic imports."""

import uuid
from typing import Literal, cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import GENERIC_ID_STRATEGY_KEY
from app.core.exceptions import AccountNotFoundError, ImportNotAllowedError
from app.repositories.account_repository import AccountRepository
from app.repositories.broker_raw_transaction_repository import BrokerRawTransactionRepository
from app.repositories.corporate_action_repository import CorporateActionRepository
from app.schemas.generic_import import ImportPreviewResult
from app.services.brokers.credentials import resolve_optional_property
from app.services.brokers.registry import adapter_for_account_type
from app.services.import_account_service import ImportAccountService
from app.utils.raw_identity import stamped_raw_id


class ImportPreviewService:
    """Validate through the adapter and read existing state; never write."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind read repositories and import authorization to the session."""
        self._session = session
        self._accounts = AccountRepository(session)
        self._raw = BrokerRawTransactionRepository(session)
        self._actions = CorporateActionRepository(session)
        self._authorization = ImportAccountService(session)

    async def preview(
        self,
        content: bytes,
        filename: str,
        portfolio_id: uuid.UUID,
        account_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> ImportPreviewResult:
        """Report fill novelty, strategy compatibility and split conflicts."""
        extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        await self._authorization.validate_file(account_id, portfolio_id, user_id, extension)
        account = await self._accounts.get_by_id(account_id, user_id, portfolio_id)
        if account is None:
            raise AccountNotFoundError("Account not found")
        adapter = adapter_for_account_type(account.type)
        if adapter is None or adapter.file_import is None or adapter.policy.id_strategy_property != GENERIC_ID_STRATEGY_KEY:
            raise ImportNotAllowedError("Preview is available only for generic file imports")
        batch = adapter.file_import.parse(content, filename)
        recorded = resolve_optional_property(account, (GENERIC_ID_STRATEGY_KEY,))
        ids = [stamped_raw_id(rec.id, str(user_id), str(account_id), adapter.policy.account_scoped_identity) for rec in batch.executions]
        # Disabling autoflush makes the no-write contract explicit even when a
        # caller has unrelated pending ORM state in the shared session.
        with self._session.no_autoflush:
            existing = await self._raw.list_existing_ids(ids, user_id, account_id)
            actions = await self._actions.list_by_user(user_id)
        ratios = {(action.symbol, action.date): action.ratio for action in actions}
        new_splits = 0
        conflicts = 0
        warnings = list(batch.warnings)
        for action in batch.corporate_actions:
            key = (action.symbol, action.date)
            if key not in ratios:
                new_splits += 1
                ratios[key] = action.ratio
            elif ratios[key] != action.ratio:
                conflicts += 1
                warnings.append("split_conflict: existing split ratio preserved")
        return ImportPreviewResult(
            detected_strategy=cast(Literal["external_id", "fingerprint"], batch.id_strategy),
            recorded_strategy=cast(Literal["external_id", "fingerprint"] | None, recorded),
            strategy_conflict=recorded is not None and recorded != batch.id_strategy,
            total=len(ids),
            new=len(ids) - len(existing),
            already_imported=len(existing),
            suppressed=sum(row.suppressed for row in existing),
            new_splits=new_splits,
            conflicting_splits=conflicts,
            warnings=warnings,
        )
