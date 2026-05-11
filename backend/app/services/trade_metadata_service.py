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
from app.repositories.taxonomy_repository import TaxonomyRepository
from app.repositories.trade_annotation_repository import TradeAnnotationRepository
from app.repositories.trade_repository import TradeRepository
from app.repositories.trade_taxonomy_repository import TradeTaxonomyRepository
from app.utils.annotation_mapping import map_value_to_column


class TradeMetadataService:
    """Business rules for trade metadata assignment endpoints."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._trade_repo = TradeRepository(session)
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
        if taxonomy.scope not in {"trades", "both"}:
            raise MetadataAssignmentValidationError("taxonomy scope is incompatible with trades")
        try:
            async with self._session.begin_nested():
                await self._trade_taxonomy_repo.assign(trade_id, taxonomy_id)
        except IntegrityError as exc:
            raise MetadataAssignmentValidationError("taxonomy is already assigned to this trade") from exc

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

    async def assign_annotation(
        self,
        trade_id: uuid.UUID,
        annotation_definition_id: uuid.UUID,
        value: Any,
        user_id: uuid.UUID,
    ) -> None:
        await self._ensure_trade_exists(trade_id, user_id)
        definition = await self._annotation_definition_repo.get_by_id(annotation_definition_id)
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

    async def update_annotation(
        self,
        trade_id: uuid.UUID,
        annotation_definition_id: uuid.UUID,
        value: Any,
        user_id: uuid.UUID,
    ) -> None:
        await self._ensure_trade_exists(trade_id, user_id)
        definition = await self._annotation_definition_repo.get_by_id(annotation_definition_id)
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

    def _validate_annotation_assignment(
        self,
        definition: AnnotationDefinition,
        value: Any,
    ) -> dict[str, Any]:
        if definition.is_archived:
            raise MetadataAssignmentValidationError("cannot assign archived annotation definition")
        if definition.scope not in {"trades", "both"}:
            raise MetadataAssignmentValidationError("annotation definition scope is incompatible with trades")
        try:
            return map_value_to_column(definition.type, value, definition.scale_labels)
        except ValueError as exc:
            raise MetadataAssignmentValidationError(str(exc)) from exc
