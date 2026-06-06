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

"""Service layer for annotation definition management."""

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AnnotationDefinitionNotFoundError,
    AnnotationDefinitionValidationError,
)
from app.repositories.annotation_definition_repository import (
    AnnotationDefinitionRepository,
)
from app.schemas.annotation_definition import (
    AnnotationDefinitionCreate,
    AnnotationDefinitionResponse,
    AnnotationDefinitionUpdate,
)
from app.services.cache_service import CacheService
from app.utils.scope_utils import scope_contains


class AnnotationDefinitionService:
    """Business rules for annotation definition CRUD."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = AnnotationDefinitionRepository(session)
        self._cache = CacheService()

    async def create(
        self,
        payload: AnnotationDefinitionCreate,
        user_id: uuid.UUID | None = None,
    ) -> AnnotationDefinitionResponse:
        resolved_user_id = user_id or uuid.UUID(int=0)
        try:
            item = await self._repo.create(user_id=resolved_user_id, payload=payload)
        except IntegrityError as exc:
            raise AnnotationDefinitionValidationError("annotation definition with this name and scope already exists") from exc
        if user_id is not None:
            await self._cache.invalidate_user(user_id)
        return AnnotationDefinitionResponse.model_validate(item)

    async def list(self, user_id: uuid.UUID, scope: str | None = None, show_archived: bool = False) -> list[AnnotationDefinitionResponse]:
        if show_archived:
            items = await self._repo.list_including_archived(user_id=user_id, scope=scope)
        else:
            items = await self._repo.list(user_id=user_id, scope=scope)
        return [AnnotationDefinitionResponse.model_validate(item) for item in items]

    async def get(self, user_id: uuid.UUID, definition_id: uuid.UUID) -> AnnotationDefinitionResponse:
        item = await self._repo.get_by_id(user_id=user_id, definition_id=definition_id)
        if item is None:
            raise AnnotationDefinitionNotFoundError("annotation definition not found")
        return AnnotationDefinitionResponse.model_validate(item)

    async def update(
        self,
        definition_id: uuid.UUID,
        payload: AnnotationDefinitionUpdate,
        user_id: uuid.UUID | None = None,
    ) -> AnnotationDefinitionResponse:
        resolved_user_id = user_id or uuid.UUID(int=0)
        item = await self._repo.get_by_id(user_id=resolved_user_id, definition_id=definition_id)
        if item is None:
            raise AnnotationDefinitionNotFoundError("annotation definition not found")

        if payload.type is not None and payload.type != item.type:
            raise AnnotationDefinitionValidationError("annotation type cannot be changed")

        current_scope = item.scope
        new_scope = payload.scope
        if new_scope is not None and new_scope != current_scope:
            trade_count, checkin_count = await self._repo.count_assignments(definition_id)

            losing_trades = scope_contains(current_scope, "trades") and not scope_contains(new_scope, "trades")
            losing_checkins = scope_contains(current_scope, "checkins") and not scope_contains(new_scope, "checkins")
            if (losing_trades and trade_count > 0) or (losing_checkins and checkin_count > 0):
                raise AnnotationDefinitionValidationError("scope narrowing is not permitted while assignments exist")

        try:
            updated = await self._repo.update(item, payload)
        except IntegrityError as exc:
            raise AnnotationDefinitionValidationError("annotation definition with this name and scope already exists") from exc
        if user_id is not None:
            await self._cache.invalidate_user(user_id)
        return AnnotationDefinitionResponse.model_validate(updated)

    async def get_assignment_counts(
        self,
        definition_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> dict[str, int]:
        """Return assignment counts for a definition, scoped to the owning user.

        Raises :class:`AnnotationDefinitionNotFoundError` when the caller does
        not own the definition or when it does not exist.
        """
        item = await self._repo.get_by_id(user_id=user_id, definition_id=definition_id)
        if item is None:
            raise AnnotationDefinitionNotFoundError("annotation definition not found")
        trade_count, checkin_count = await self._repo.count_assignments(definition_id)
        return {
            "trade_count": trade_count,
            "checkin_count": checkin_count,
            "total_count": trade_count + checkin_count,
        }

    async def archive(self, definition_id: uuid.UUID, user_id: uuid.UUID) -> AnnotationDefinitionResponse:
        item = await self._repo.get_by_id(user_id=user_id, definition_id=definition_id)
        if item is None:
            raise AnnotationDefinitionNotFoundError("annotation definition not found")
        archived = await self._repo.archive(item)
        await self._cache.invalidate_user(user_id)
        return AnnotationDefinitionResponse.model_validate(archived)

    async def unarchive(self, definition_id: uuid.UUID, user_id: uuid.UUID) -> AnnotationDefinitionResponse:
        item = await self._repo.get_by_id(user_id=user_id, definition_id=definition_id)
        if item is None:
            raise AnnotationDefinitionNotFoundError("annotation definition not found")
        unarchived = await self._repo.unarchive(item)
        await self._cache.invalidate_user(user_id)
        return AnnotationDefinitionResponse.model_validate(unarchived)

    async def delete(
        self,
        definition_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        force: bool = False,
    ) -> AnnotationDefinitionResponse | None:
        resolved_user_id = user_id or uuid.UUID(int=0)
        item = await self._repo.get_by_id(user_id=resolved_user_id, definition_id=definition_id)
        if item is None:
            raise AnnotationDefinitionNotFoundError("annotation definition not found")

        if force:
            await self._repo.delete_assignments(definition_id)
            await self._repo.delete(item)
            if user_id is not None:
                await self._cache.invalidate_user(user_id)
            return None

        trade_count, checkin_count = await self._repo.count_assignments(definition_id)
        if trade_count + checkin_count == 0:
            await self._repo.delete(item)
            if user_id is not None:
                await self._cache.invalidate_user(user_id)
            return None

        archived = await self._repo.archive(item)
        if user_id is not None:
            await self._cache.invalidate_user(user_id)
        return AnnotationDefinitionResponse.model_validate(archived)
