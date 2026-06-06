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

"""Service layer for taxonomy definition management."""

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import TaxonomyNotFoundError, TaxonomyValidationError
from app.repositories.taxonomy_repository import TaxonomyRepository
from app.schemas.taxonomy import TaxonomyCreate, TaxonomyResponse, TaxonomyUpdate
from app.services.cache_service import CacheService
from app.utils.scope_utils import VALID_SCOPE_TOKENS, scope_contains


class TaxonomyService:
    """Business rules for taxonomy definition CRUD."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = TaxonomyRepository(session)
        self._cache = CacheService()

    async def create(
        self,
        payload: TaxonomyCreate,
        user_id: uuid.UUID | None = None,
    ) -> TaxonomyResponse:
        resolved_user_id = user_id or uuid.UUID(int=0)
        try:
            item = await self._repo.create(user_id=resolved_user_id, payload=payload)
        except IntegrityError as exc:
            raise TaxonomyValidationError("taxonomy with this name and scope already exists") from exc
        if user_id is not None:
            await self._cache.invalidate_user(user_id)
        return TaxonomyResponse.model_validate(item)

    async def list(self, user_id: uuid.UUID, scope: str | None = None, show_archived: bool = False) -> list[TaxonomyResponse]:
        if scope is not None and scope not in VALID_SCOPE_TOKENS:
            raise TaxonomyValidationError(f"Invalid scope filter '{scope}'. Allowed: {sorted(VALID_SCOPE_TOKENS)}")
        if show_archived:
            items = await self._repo.list_including_archived(user_id=user_id, scope=scope)
            return [TaxonomyResponse.model_validate(item) for item in items]
        pairs = await self._repo.list_with_usage_counts(user_id=user_id, scope=scope)
        return [TaxonomyResponse.model_validate(item).model_copy(update={"usage_count": count}) for item, count in pairs]

    async def get(self, user_id: uuid.UUID, taxonomy_id: uuid.UUID) -> TaxonomyResponse:
        item = await self._repo.get_by_id(user_id=user_id, taxonomy_id=taxonomy_id)
        if item is None:
            raise TaxonomyNotFoundError("taxonomy not found")
        return TaxonomyResponse.model_validate(item)

    async def update(
        self,
        taxonomy_id: uuid.UUID,
        payload: TaxonomyUpdate,
        user_id: uuid.UUID | None = None,
    ) -> TaxonomyResponse:
        resolved_user_id = user_id or uuid.UUID(int=0)
        item = await self._repo.get_by_id(user_id=resolved_user_id, taxonomy_id=taxonomy_id)
        if item is None:
            raise TaxonomyNotFoundError("taxonomy not found")

        current_scope = item.scope
        new_scope = payload.scope
        if new_scope is not None and new_scope != current_scope:
            trade_count, checkin_count, playbook_count = await self._repo.count_assignments(taxonomy_id)

            losing_trades = scope_contains(current_scope, "trades") and not scope_contains(new_scope, "trades")
            losing_checkins = scope_contains(current_scope, "checkins") and not scope_contains(new_scope, "checkins")
            losing_playbook = scope_contains(current_scope, "playbook") and not scope_contains(new_scope, "playbook")

            if (losing_trades and trade_count > 0) or (losing_checkins and checkin_count > 0) or (losing_playbook and playbook_count > 0):
                raise TaxonomyValidationError(
                    f"Cannot remove a scope that is currently in use "
                    f"(trade_count={trade_count}, checkin_count={checkin_count}, playbook_count={playbook_count})"
                )

        try:
            updated = await self._repo.update(item, payload)
        except IntegrityError as exc:
            raise TaxonomyValidationError("taxonomy with this name and scope already exists") from exc
        if user_id is not None:
            await self._cache.invalidate_user(user_id)
        return TaxonomyResponse.model_validate(updated)

    async def get_assignment_counts(
        self,
        taxonomy_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> dict[str, int]:
        """Return assignment counts for a taxonomy, scoped to the owning user.

        Raises :class:`TaxonomyNotFoundError` when the caller does not own the
        taxonomy or when it does not exist.
        """
        item = await self._repo.get_by_id(user_id=user_id, taxonomy_id=taxonomy_id)
        if item is None:
            raise TaxonomyNotFoundError("taxonomy not found")
        trade_count, checkin_count, playbook_count = await self._repo.count_assignments(taxonomy_id)
        return {
            "trade_count": trade_count,
            "checkin_count": checkin_count,
            "playbook_count": playbook_count,
            "total_count": trade_count + checkin_count + playbook_count,
        }

    async def archive(self, taxonomy_id: uuid.UUID, user_id: uuid.UUID) -> TaxonomyResponse:
        item = await self._repo.get_by_id(user_id=user_id, taxonomy_id=taxonomy_id)
        if item is None:
            raise TaxonomyNotFoundError("taxonomy not found")
        archived = await self._repo.archive(item)
        await self._cache.invalidate_user(user_id)
        return TaxonomyResponse.model_validate(archived)

    async def unarchive(self, taxonomy_id: uuid.UUID, user_id: uuid.UUID) -> TaxonomyResponse:
        item = await self._repo.get_by_id(user_id=user_id, taxonomy_id=taxonomy_id)
        if item is None:
            raise TaxonomyNotFoundError("taxonomy not found")
        unarchived = await self._repo.unarchive(item)
        await self._cache.invalidate_user(user_id)
        return TaxonomyResponse.model_validate(unarchived)

    async def delete(
        self,
        taxonomy_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        force: bool = False,
    ) -> TaxonomyResponse | None:
        resolved_user_id = user_id or uuid.UUID(int=0)
        item = await self._repo.get_by_id(user_id=resolved_user_id, taxonomy_id=taxonomy_id)
        if item is None:
            raise TaxonomyNotFoundError("taxonomy not found")

        if force:
            await self._repo.delete_assignments(taxonomy_id)
            await self._repo.delete(item)
            if user_id is not None:
                await self._cache.invalidate_user(user_id)
            return None

        assignment_counts = await self._repo.count_assignments(taxonomy_id)
        trade_count, checkin_count, playbook_count = assignment_counts
        if trade_count + checkin_count + playbook_count == 0:
            await self._repo.delete(item)
            if user_id is not None:
                await self._cache.invalidate_user(user_id)
            return None

        archived = await self._repo.archive(item)
        if user_id is not None:
            await self._cache.invalidate_user(user_id)
        return TaxonomyResponse.model_validate(archived)
