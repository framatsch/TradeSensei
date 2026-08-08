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

"""Service layer for trade taxonomy and annotation assignments."""

import uuid
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    MetadataAssignmentNotFoundError,
    MetadataAssignmentValidationError,
    TaxonomyNotFoundError,
    TradeNotFoundError,
)
from app.models.annotation_definition import AnnotationDefinition
from app.repositories.annotation_definition_repository import (
    AnnotationDefinitionRepository,
)
from app.repositories.execution import ExecutionRepository
from app.repositories.taxonomy_repository import TaxonomyRepository
from app.repositories.trade_annotation_repository import TradeAnnotationRepository
from app.repositories.trade_repository import TradeRepository
from app.repositories.trade_taxonomy_repository import TradeTaxonomyRepository
from app.utils.annotation_mapping import map_value_to_column
from app.utils.scope_utils import scope_contains


class TradeMetadataService:
    """Business rules for trade metadata assignment endpoints."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._trade_repo = TradeRepository(session)
        self._execution_repo = ExecutionRepository(session)
        self._taxonomy_repo = TaxonomyRepository(session)
        self._annotation_definition_repo = AnnotationDefinitionRepository(session)
        self._trade_taxonomy_repo = TradeTaxonomyRepository(session)
        self._trade_annotation_repo = TradeAnnotationRepository(session)

    async def _ensure_trade_exists(self, trade_id: uuid.UUID, user_id: uuid.UUID) -> None:
        trade = await self._trade_repo.get_by_id(trade_id, user_id)
        if trade is None:
            raise TradeNotFoundError("trade not found")

    async def assign_taxonomy(
        self,
        trade_id: uuid.UUID,
        taxonomy_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        await self._ensure_trade_exists(trade_id, user_id)
        taxonomy = await self._taxonomy_repo.get_by_id(user_id=user_id, taxonomy_id=taxonomy_id)
        if taxonomy is None:
            raise TaxonomyNotFoundError("taxonomy not found")
        if taxonomy.is_archived:
            raise MetadataAssignmentValidationError("cannot assign archived taxonomy")
        if not scope_contains(taxonomy.scope, "trades"):
            raise MetadataAssignmentValidationError("taxonomy scope is incompatible with trades")
        try:
            async with self._session.begin_nested():
                await self._trade_taxonomy_repo.assign(trade_id, taxonomy_id)
        except IntegrityError as exc:
            raise MetadataAssignmentValidationError("taxonomy is already assigned to this trade") from exc
        await self._trade_repo.mark_manually_edited(trade_id, user_id)
        await self._execution_repo.mark_user_modified_for_trade(trade_id)

    async def remove_taxonomy(
        self,
        trade_id: uuid.UUID,
        taxonomy_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        await self._ensure_trade_exists(trade_id, user_id)
        removed = await self._trade_taxonomy_repo.remove(trade_id, taxonomy_id)
        if not removed:
            raise MetadataAssignmentNotFoundError("taxonomy assignment not found")
        await self._trade_repo.mark_manually_edited(trade_id, user_id)
        await self._execution_repo.mark_user_modified_for_trade(trade_id)

    async def assign_annotation(
        self,
        trade_id: uuid.UUID,
        annotation_definition_id: uuid.UUID,
        value: Any,
        user_id: uuid.UUID,
    ) -> None:
        await self._ensure_trade_exists(trade_id, user_id)
        definition = await self._annotation_definition_repo.get_by_id(
            user_id=user_id,
            definition_id=annotation_definition_id,
        )
        if definition is None:
            raise MetadataAssignmentValidationError("annotation definition not found")
        typed_values = self._validate_annotation_assignment(definition, value)
        try:
            async with self._session.begin_nested():
                await self._trade_annotation_repo.assign(
                    trade_id,
                    annotation_definition_id,
                    typed_values,
                )
        except IntegrityError as exc:
            raise MetadataAssignmentValidationError("annotation is already assigned to this trade") from exc
        await self._trade_repo.mark_manually_edited(trade_id, user_id)
        await self._execution_repo.mark_user_modified_for_trade(trade_id)

    async def update_annotation(
        self,
        trade_id: uuid.UUID,
        annotation_definition_id: uuid.UUID,
        value: Any,
        user_id: uuid.UUID,
    ) -> None:
        await self._ensure_trade_exists(trade_id, user_id)
        definition = await self._annotation_definition_repo.get_by_id(
            user_id=user_id,
            definition_id=annotation_definition_id,
        )
        if definition is None:
            raise MetadataAssignmentValidationError("annotation definition not found")
        typed_values = self._validate_annotation_assignment(definition, value)
        assignment = await self._trade_annotation_repo.update(
            trade_id,
            annotation_definition_id,
            typed_values,
        )
        if assignment is None:
            raise MetadataAssignmentNotFoundError("annotation assignment not found")
        await self._trade_repo.mark_manually_edited(trade_id, user_id)
        await self._execution_repo.mark_user_modified_for_trade(trade_id)

    async def remove_annotation(
        self,
        trade_id: uuid.UUID,
        annotation_definition_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        await self._ensure_trade_exists(trade_id, user_id)
        removed = await self._trade_annotation_repo.remove(
            trade_id,
            annotation_definition_id,
        )
        if not removed:
            raise MetadataAssignmentNotFoundError("annotation assignment not found")
        await self._trade_repo.mark_manually_edited(trade_id, user_id)
        await self._execution_repo.mark_user_modified_for_trade(trade_id)

    def _validate_annotation_assignment(
        self,
        definition: AnnotationDefinition,
        value: Any,
    ) -> dict[str, Any]:
        if definition.is_archived:
            raise MetadataAssignmentValidationError("cannot assign archived annotation definition")
        if not scope_contains(definition.scope, "trades"):
            raise MetadataAssignmentValidationError("annotation definition scope is incompatible with trades")
        try:
            return map_value_to_column(definition.type, value, definition.scale_labels)
        except ValueError as exc:
            raise MetadataAssignmentValidationError(str(exc)) from exc
