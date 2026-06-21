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
            {"name": "Bullish", "scope": "checkins", "color_hex": "#22c55e", "icon_identifier": "trending-up"},
            {"name": "Bearish", "scope": "checkins", "color_hex": "#ef4444", "icon_identifier": "trending-down"},
            {"name": "Sideways", "scope": "checkins", "color_hex": "#f59e0b", "icon_identifier": "minus"},
            {"name": "Volatile", "scope": "checkins", "color_hex": "#a855f7", "icon_identifier": "activity"},
            {"name": "FOMO", "scope": "trades", "color_hex": "#ec4899", "icon_identifier": "alert-circle"},
            {"name": "Discipline", "scope": "trades", "color_hex": "#3b82f6", "icon_identifier": "shield"},
            {"name": "High Conviction", "scope": "trades", "color_hex": "#facc15", "icon_identifier": "zap"},
            {"name": "Stop Loss", "scope": "trades", "color_hex": "#ef4444", "icon_identifier": "octagon"},
            {"name": "Textbook Trade", "scope": "trades", "color_hex": "#fbbf24", "icon_identifier": "award"},
            {"name": "Breakout", "scope": "trades,checkins", "color_hex": "#10b981", "icon_identifier": "arrow-up-right"},
            {"name": "Mean Reversion", "scope": "trades,checkins", "color_hex": "#6366f1", "icon_identifier": "repeat"},
            {"name": "Momentum", "scope": "trades,checkins", "color_hex": "#f97316", "icon_identifier": "rocket"},
            {"name": "Trend Following", "scope": "trades,checkins", "color_hex": "#06b6d4", "icon_identifier": "trending-up"},
        ]
        stmt = pg_insert(Taxonomy).values(
            [
                {
                    "user_id": user_id,
                    "name": row["name"],
                    "scope": row["scope"],
                    "color_hex": row["color_hex"],
                    "description": None,
                    "icon_identifier": row["icon_identifier"],
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

    async def list(self, user_id: uuid.UUID, scope: str | None = None) -> builtins.list[Taxonomy]:
        stmt = select(Taxonomy).where(Taxonomy.user_id == user_id, Taxonomy.is_archived.is_(False)).order_by(Taxonomy.name.asc())
        if scope is not None:
            # Match taxonomies whose comma-separated scope contains the requested token.
            stmt = stmt.where(
                (Taxonomy.scope == scope)
                | Taxonomy.scope.like(f"{scope},%")
                | Taxonomy.scope.like(f"%,{scope}")
                | Taxonomy.scope.like(f"%,{scope},%")
            )
        result = await self._session.execute(stmt)
        return builtins.list(result.scalars().all())

    async def list_with_usage_counts(self, user_id: uuid.UUID, scope: str | None = None) -> builtins.list[tuple[Taxonomy, int]]:
        """Return active taxonomies together with their total assignment count."""
        trade_count = (
            select(func.count())
            .select_from(TradeTaxonomy)
            .where(TradeTaxonomy.taxonomy_id == Taxonomy.id)
            .correlate(Taxonomy)
            .scalar_subquery()
        )
        checkin_count = (
            select(func.count())
            .select_from(CheckinTaxonomy)
            .where(CheckinTaxonomy.taxonomy_id == Taxonomy.id)
            .correlate(Taxonomy)
            .scalar_subquery()
        )
        playbook_count = (
            select(func.count())
            .select_from(PlaybookTaxonomy)
            .where(PlaybookTaxonomy.taxonomy_id == Taxonomy.id)
            .correlate(Taxonomy)
            .scalar_subquery()
        )
        stmt = (
            select(Taxonomy, (trade_count + checkin_count + playbook_count).label("usage_count"))
            .where(Taxonomy.user_id == user_id, Taxonomy.is_archived.is_(False))
            .order_by(Taxonomy.name.asc())
        )
        if scope is not None:
            stmt = stmt.where(
                (Taxonomy.scope == scope)
                | Taxonomy.scope.like(f"{scope},%")
                | Taxonomy.scope.like(f"%,{scope}")
                | Taxonomy.scope.like(f"%,{scope},%")
            )
        result = await self._session.execute(stmt)
        return [(row.Taxonomy, int(row.usage_count)) for row in result.all()]

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

    async def delete_assignments(self, taxonomy_id: uuid.UUID) -> None:
        from sqlalchemy import delete
        await self._session.execute(delete(TradeTaxonomy).where(TradeTaxonomy.taxonomy_id == taxonomy_id))
        await self._session.execute(delete(CheckinTaxonomy).where(CheckinTaxonomy.taxonomy_id == taxonomy_id))
        await self._session.execute(delete(PlaybookTaxonomy).where(PlaybookTaxonomy.taxonomy_id == taxonomy_id))
        await self._session.flush()

    async def delete(self, taxonomy: Taxonomy) -> None:
        await self._session.delete(taxonomy)
        await self._session.flush()

    async def archive(self, taxonomy: Taxonomy) -> Taxonomy:
        taxonomy.is_archived = True
        self._session.add(taxonomy)
        await self._session.flush()
        await self._session.refresh(taxonomy)
        return taxonomy

    async def unarchive(self, taxonomy: Taxonomy) -> Taxonomy:
        taxonomy.is_archived = False
        self._session.add(taxonomy)
        await self._session.flush()
        await self._session.refresh(taxonomy)
        return taxonomy

    async def list_including_archived(self, user_id: uuid.UUID, scope: str | None = None) -> builtins.list[Taxonomy]:
        stmt = select(Taxonomy).where(Taxonomy.user_id == user_id).order_by(Taxonomy.name.asc())
        if scope is not None:
            stmt = stmt.where(
                (Taxonomy.scope == scope)
                | Taxonomy.scope.like(f"{scope},%")
                | Taxonomy.scope.like(f"%,{scope}")
                | Taxonomy.scope.like(f"%,{scope},%")
            )
        result = await self._session.execute(stmt)
        return builtins.list(result.scalars().all())

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
        return builtins.list(result.scalars().all())
