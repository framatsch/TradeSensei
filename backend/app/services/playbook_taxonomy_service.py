"""Service layer for playbook taxonomy assignments."""

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    MetadataAssignmentNotFoundError,
    MetadataAssignmentValidationError,
    PlaybookNotFoundError,
    TaxonomyNotFoundError,
)
from app.repositories.playbook_repository import PlaybookRepository
from app.repositories.playbook_taxonomy_repository import PlaybookTaxonomyRepository
from app.repositories.taxonomy_repository import TaxonomyRepository
from app.schemas.taxonomy import TaxonomyResponse


class PlaybookTaxonomyService:
    """Business rules for assigning taxonomies to playbooks."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._playbook_repo = PlaybookRepository(session)
        self._taxonomy_repo = TaxonomyRepository(session)
        self._playbook_taxonomy_repo = PlaybookTaxonomyRepository(session)

    async def _ensure_playbook_exists(self, playbook_id: uuid.UUID, user_id: uuid.UUID) -> None:
        playbook = await self._playbook_repo.get_by_id(playbook_id=playbook_id, user_id=user_id)
        if playbook is None:
            raise PlaybookNotFoundError("playbook not found")

    async def assign(
        self,
        playbook_id: uuid.UUID,
        taxonomy_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        await self._ensure_playbook_exists(playbook_id, user_id)
        taxonomy = await self._taxonomy_repo.get_by_id(user_id=user_id, taxonomy_id=taxonomy_id)
        if taxonomy is None:
            raise TaxonomyNotFoundError("taxonomy not found")
        if taxonomy.is_archived:
            raise MetadataAssignmentValidationError("cannot assign archived taxonomy")
        if taxonomy.scope not in {"playbook", "both"}:
            raise MetadataAssignmentValidationError("taxonomy scope is incompatible with playbooks")
        try:
            async with self._session.begin_nested():
                await self._playbook_taxonomy_repo.assign(playbook_id, taxonomy_id)
        except IntegrityError as exc:
            raise MetadataAssignmentValidationError("taxonomy is already assigned to this playbook") from exc

    async def list(self, playbook_id: uuid.UUID, user_id: uuid.UUID) -> list[TaxonomyResponse]:
        await self._ensure_playbook_exists(playbook_id, user_id)
        assignments = await self._playbook_taxonomy_repo.list_for_playbook(playbook_id)
        taxonomy_ids = [a.taxonomy_id for a in assignments]
        if not taxonomy_ids:
            return []
        taxonomies = await self._taxonomy_repo.get_many_by_ids(taxonomy_ids=taxonomy_ids, user_id=user_id)
        return [TaxonomyResponse.model_validate(t) for t in taxonomies]

    async def remove(
        self,
        playbook_id: uuid.UUID,
        taxonomy_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        await self._ensure_playbook_exists(playbook_id, user_id)
        removed = await self._playbook_taxonomy_repo.remove(playbook_id, taxonomy_id)
        if not removed:
            raise MetadataAssignmentNotFoundError("taxonomy assignment not found")
