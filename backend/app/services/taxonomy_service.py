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

    async def list(self, user_id: uuid.UUID, scope: str | None = None) -> list[TaxonomyResponse]:
        items = await self._repo.list(user_id=user_id, scope=scope)
        return [TaxonomyResponse.model_validate(item) for item in items]

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
            assignment_counts = await self._repo.count_assignments(taxonomy_id)
            trade_count, checkin_count = assignment_counts[0], assignment_counts[1]
            playbook_count = assignment_counts[2] if len(assignment_counts) > 2 else 0
            # Narrowing away from a scope that has existing assignments is blocked
            losing_trades = current_scope in {"trades", "both"} and new_scope not in {"trades", "both"}
            losing_checkins = current_scope in {"checkins", "both"} and new_scope not in {"checkins", "both"}
            losing_playbook = current_scope in {"playbook", "both"} and new_scope not in {"playbook", "both"}
            if (losing_trades and trade_count > 0) or (losing_checkins and checkin_count > 0) or (losing_playbook and playbook_count > 0):
                raise TaxonomyValidationError("scope narrowing is not permitted while assignments exist")

        try:
            updated = await self._repo.update(item, payload)
        except IntegrityError as exc:
            raise TaxonomyValidationError("taxonomy with this name and scope already exists") from exc
        if user_id is not None:
            await self._cache.invalidate_user(user_id)
        return TaxonomyResponse.model_validate(updated)

    async def delete(
        self,
        taxonomy_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> TaxonomyResponse | None:
        resolved_user_id = user_id or uuid.UUID(int=0)
        item = await self._repo.get_by_id(user_id=resolved_user_id, taxonomy_id=taxonomy_id)
        if item is None:
            raise TaxonomyNotFoundError("taxonomy not found")

        assignment_counts = await self._repo.count_assignments(taxonomy_id)
        trade_count, checkin_count = assignment_counts[0], assignment_counts[1]
        playbook_count = assignment_counts[2] if len(assignment_counts) > 2 else 0
        if trade_count + checkin_count + playbook_count == 0:
            await self._repo.delete(item)
            if user_id is not None:
                await self._cache.invalidate_user(user_id)
            return None

        archived = await self._repo.archive(item)
        if user_id is not None:
            await self._cache.invalidate_user(user_id)
        return TaxonomyResponse.model_validate(archived)
