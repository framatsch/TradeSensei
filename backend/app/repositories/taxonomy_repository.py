"""Repository for taxonomy definition persistence and assignment counts."""

from __future__ import annotations

import builtins
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.checkin_taxonomy import CheckinTaxonomy
from app.models.playbook_taxonomy import PlaybookTaxonomy
from app.models.taxonomy import Taxonomy
from app.models.trade_taxonomy import TradeTaxonomy
from app.schemas.taxonomy import TaxonomyCreate, TaxonomyUpdate


class TaxonomyRepository:
    """Data-access operations for taxonomy definitions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def seed_defaults(self, user_id: uuid.UUID) -> None:
        """Insert default taxonomies if they do not exist."""
        defaults: list[dict[str, Any]] = [
            {"name": "Mistakes", "scope": "trades", "color_hex": "#ef4444", "description": "Common trading mistakes"},
            {"name": "Setups", "scope": "trades", "color_hex": "#3b82f6", "description": "Core trading setups"},
            {"name": "Emotions", "scope": "both", "color_hex": "#f59e0b", "description": "Psychological state"},
        ]
        stmt = pg_insert(Taxonomy).values(
            [
                {
                    "user_id": user_id,
                    "name": row["name"],
                    "scope": row["scope"],
                    "color_hex": row["color_hex"],
                    "description": row["description"],
                    "is_archived": False,
                }
                for row in defaults
            ]
        )
        stmt = stmt.on_conflict_do_nothing(
            constraint="uq_taxonomies_user_name_scope",
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def create(self, user_id: uuid.UUID, payload: TaxonomyCreate) -> Taxonomy:
        taxonomy = Taxonomy(user_id=user_id, **payload.model_dump())
        self._session.add(taxonomy)
        await self._session.flush()
        await self._session.refresh(taxonomy)
        return taxonomy

    async def get_by_id(self, user_id: uuid.UUID, taxonomy_id: uuid.UUID) -> Taxonomy | None:
        result = await self._session.execute(select(Taxonomy).where(Taxonomy.user_id == user_id, Taxonomy.id == taxonomy_id))
        return result.scalar_one_or_none()

    async def list(self, user_id: uuid.UUID, scope: str | None = None) -> list[Taxonomy]:
        stmt = select(Taxonomy).where(Taxonomy.user_id == user_id, Taxonomy.is_archived.is_(False)).order_by(Taxonomy.name.asc())
        if scope is not None:
            stmt = stmt.where(Taxonomy.scope.in_([scope, "both"]))
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, taxonomy: Taxonomy, payload: TaxonomyUpdate) -> Taxonomy:
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(taxonomy, field, value)
        self._session.add(taxonomy)
        await self._session.flush()
        await self._session.refresh(taxonomy)
        return taxonomy

    async def count_assignments(self, taxonomy_id: uuid.UUID) -> tuple[int, int, int]:
        trade_result = await self._session.execute(select(func.count()).select_from(TradeTaxonomy).where(TradeTaxonomy.taxonomy_id == taxonomy_id))
        checkin_result = await self._session.execute(select(func.count()).select_from(CheckinTaxonomy).where(CheckinTaxonomy.taxonomy_id == taxonomy_id))
        playbook_result = await self._session.execute(select(func.count()).select_from(PlaybookTaxonomy).where(PlaybookTaxonomy.taxonomy_id == taxonomy_id))
        return int(trade_result.scalar_one() or 0), int(checkin_result.scalar_one() or 0), int(playbook_result.scalar_one() or 0)

    async def delete(self, taxonomy: Taxonomy) -> None:
        await self._session.delete(taxonomy)
        await self._session.flush()

    async def archive(self, taxonomy: Taxonomy) -> Taxonomy:
        taxonomy.is_archived = True
        self._session.add(taxonomy)
        await self._session.flush()
        await self._session.refresh(taxonomy)
        return taxonomy

    async def get_many_by_ids(
        self,
        taxonomy_ids: builtins.list[uuid.UUID],
        user_id: uuid.UUID,
    ) -> builtins.list[Taxonomy]:
        """Return taxonomies by ids scoped to one user."""
        if not taxonomy_ids:
            return []
        result = await self._session.execute(
            select(Taxonomy).where(
                Taxonomy.id.in_(taxonomy_ids),
                Taxonomy.user_id == user_id,
                Taxonomy.is_archived.is_(False),
            )
        )
        return list(result.scalars().all())
