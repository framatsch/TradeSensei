"""Service layer for taxonomy definition management."""

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import TaxonomyNotFoundError, TaxonomyValidationError
from app.repositories.taxonomy_repository import TaxonomyRepository
from app.schemas.taxonomy import TaxonomyCreate, TaxonomyResponse, TaxonomyUpdate


class TaxonomyService:
    """Business rules for taxonomy definition CRUD."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = TaxonomyRepository(session)

    async def create(self, user_id: uuid.UUID, payload: TaxonomyCreate) -> TaxonomyResponse:
        try:
            item = await self._repo.create(user_id=user_id, payload=payload)
        except IntegrityError as exc:
            raise TaxonomyValidationError("taxonomy with this name and scope already exists") from exc
        return TaxonomyResponse.model_validate(item)

    async def list(self, user_id: uuid.UUID, scope: str | None = None) -> list[TaxonomyResponse]:
        items = await self._repo.list(user_id=user_id, scope=scope)
        return [TaxonomyResponse.model_validate(item) for item in items]

    async def get(self, user_id: uuid.UUID, taxonomy_id: uuid.UUID) -> TaxonomyResponse:
        item = await self._repo.get_by_id(user_id=user_id, taxonomy_id=taxonomy_id)
        if item is None:
            raise TaxonomyNotFoundError("taxonomy not found")
        return TaxonomyResponse.model_validate(item)

    async def update(self, user_id: uuid.UUID, taxonomy_id: uuid.UUID, payload: TaxonomyUpdate) -> TaxonomyResponse:
        item = await self._repo.get_by_id(user_id=user_id, taxonomy_id=taxonomy_id)
        if item is None:
            raise TaxonomyNotFoundError("taxonomy not found")

        current_scope = item.scope
        new_scope = payload.scope
        if new_scope is not None and new_scope != current_scope and current_scope == "both":
            trade_count, checkin_count = await self._repo.count_assignments(taxonomy_id)
            narrowing_to_trades = new_scope == "trades" and checkin_count > 0
            narrowing_to_checkins = new_scope == "checkins" and trade_count > 0
            if narrowing_to_trades or narrowing_to_checkins:
                raise TaxonomyValidationError("scope narrowing is not permitted while assignments exist")

        try:
            updated = await self._repo.update(item, payload)
        except IntegrityError as exc:
            raise TaxonomyValidationError("taxonomy with this name and scope already exists") from exc
        return TaxonomyResponse.model_validate(updated)

    async def delete(self, user_id: uuid.UUID, taxonomy_id: uuid.UUID) -> TaxonomyResponse | None:
        item = await self._repo.get_by_id(user_id=user_id, taxonomy_id=taxonomy_id)
        if item is None:
            raise TaxonomyNotFoundError("taxonomy not found")

        trade_count, checkin_count = await self._repo.count_assignments(taxonomy_id)
        if trade_count + checkin_count == 0:
            await self._repo.delete(item)
            return None

        archived = await self._repo.archive(item)
        return TaxonomyResponse.model_validate(archived)
