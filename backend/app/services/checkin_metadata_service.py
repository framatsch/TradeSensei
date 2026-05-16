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

"""Service layer for check-in taxonomy and annotation assignments."""

import uuid
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    DailyCheckinNotFoundError,
    MetadataAssignmentNotFoundError,
    MetadataAssignmentValidationError,
    TaxonomyNotFoundError,
)
from app.models.annotation_definition import AnnotationDefinition
from app.repositories.annotation_definition_repository import (
    AnnotationDefinitionRepository,
)
from app.repositories.checkin_annotation_repository import CheckinAnnotationRepository
from app.repositories.checkin_taxonomy_repository import CheckinTaxonomyRepository
from app.repositories.daily_checkin_repository import DailyCheckinRepository
from app.repositories.taxonomy_repository import TaxonomyRepository
from app.utils.annotation_mapping import map_value_to_column


class CheckinMetadataService:
    """Business rules for check-in metadata assignment endpoints."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._checkin_repo = DailyCheckinRepository(session)
        self._taxonomy_repo = TaxonomyRepository(session)
        self._annotation_definition_repo = AnnotationDefinitionRepository(session)
        self._checkin_taxonomy_repo = CheckinTaxonomyRepository(session)
        self._checkin_annotation_repo = CheckinAnnotationRepository(session)

    async def _ensure_checkin_exists(self, checkin_id: uuid.UUID, user_id: uuid.UUID) -> None:
        checkin = await self._checkin_repo.get_by_id_and_user(checkin_id, user_id)
        if checkin is None:
            raise DailyCheckinNotFoundError("daily check-in not found")

    async def assign_taxonomy(
        self,
        checkin_id: uuid.UUID,
        taxonomy_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        await self._ensure_checkin_exists(checkin_id, user_id)
        taxonomy = await self._taxonomy_repo.get_by_id(user_id=user_id, taxonomy_id=taxonomy_id)
        if taxonomy is None:
            raise TaxonomyNotFoundError("taxonomy not found")
        if taxonomy.is_archived:
            raise MetadataAssignmentValidationError("cannot assign archived taxonomy")
        if taxonomy.scope not in {"checkins", "both"}:
            raise MetadataAssignmentValidationError("taxonomy scope is incompatible with check-ins")
        try:
            async with self._session.begin_nested():
                await self._checkin_taxonomy_repo.assign(checkin_id, taxonomy_id)
        except IntegrityError as exc:
            raise MetadataAssignmentValidationError("taxonomy is already assigned to this check-in") from exc

    async def remove_taxonomy(
        self,
        checkin_id: uuid.UUID,
        taxonomy_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        await self._ensure_checkin_exists(checkin_id, user_id)
        removed = await self._checkin_taxonomy_repo.remove(checkin_id, taxonomy_id)
        if not removed:
            raise MetadataAssignmentNotFoundError("taxonomy assignment not found")

    async def assign_annotation(
        self,
        checkin_id: uuid.UUID,
        annotation_definition_id: uuid.UUID,
        value: Any,
        user_id: uuid.UUID,
    ) -> None:
        await self._ensure_checkin_exists(checkin_id, user_id)
        definition = await self._annotation_definition_repo.get_by_id(
            user_id=user_id,
            definition_id=annotation_definition_id,
        )
        if definition is None:
            raise MetadataAssignmentValidationError("annotation definition not found")
        typed_values = self._validate_annotation_assignment(definition, value)
        try:
            async with self._session.begin_nested():
                await self._checkin_annotation_repo.assign(
                    checkin_id,
                    annotation_definition_id,
                    typed_values,
                )
        except IntegrityError as exc:
            raise MetadataAssignmentValidationError("annotation is already assigned to this check-in") from exc

    async def update_annotation(
        self,
        checkin_id: uuid.UUID,
        annotation_definition_id: uuid.UUID,
        value: Any,
        user_id: uuid.UUID,
    ) -> None:
        await self._ensure_checkin_exists(checkin_id, user_id)
        definition = await self._annotation_definition_repo.get_by_id(
            user_id=user_id,
            definition_id=annotation_definition_id,
        )
        if definition is None:
            raise MetadataAssignmentValidationError("annotation definition not found")
        typed_values = self._validate_annotation_assignment(definition, value)
        assignment = await self._checkin_annotation_repo.update(
            checkin_id,
            annotation_definition_id,
            typed_values,
        )
        if assignment is None:
            raise MetadataAssignmentNotFoundError("annotation assignment not found")

    async def remove_annotation(
        self,
        checkin_id: uuid.UUID,
        annotation_definition_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        await self._ensure_checkin_exists(checkin_id, user_id)
        removed = await self._checkin_annotation_repo.remove(
            checkin_id,
            annotation_definition_id,
        )
        if not removed:
            raise MetadataAssignmentNotFoundError("annotation assignment not found")

    def _validate_annotation_assignment(
        self,
        definition: AnnotationDefinition,
        value: Any,
    ) -> dict[str, Any]:
        if definition.is_archived:
            raise MetadataAssignmentValidationError("cannot assign archived annotation definition")
        if definition.scope not in {"checkins", "both"}:
            raise MetadataAssignmentValidationError("annotation definition scope is incompatible with check-ins")
        try:
            return map_value_to_column(definition.type, value, definition.scale_labels)
        except ValueError as exc:
            raise MetadataAssignmentValidationError(str(exc)) from exc
