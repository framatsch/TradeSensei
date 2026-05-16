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

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_index import MarketIndexDefinition


class MarketIndexDefinitionRepository:
    """Repository for managing Market Index Definitions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(
        self,
        index_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> MarketIndexDefinition | None:
        result = await self.session.execute(
            select(MarketIndexDefinition).where(
                MarketIndexDefinition.id == index_id,
                MarketIndexDefinition.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        is_active: bool | None = None,
    ) -> Sequence[MarketIndexDefinition]:
        stmt = select(MarketIndexDefinition).where(MarketIndexDefinition.user_id == user_id).order_by(MarketIndexDefinition.created_at.asc())
        if is_active is not None:
            stmt = stmt.where(MarketIndexDefinition.is_active == is_active)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_ids_for_user(
        self,
        user_id: uuid.UUID,
        index_ids: Sequence[uuid.UUID],
    ) -> Sequence[MarketIndexDefinition]:
        if not index_ids:
            return []
        stmt = select(MarketIndexDefinition).where(
            MarketIndexDefinition.user_id == user_id,
            MarketIndexDefinition.id.in_(index_ids),
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_symbol_and_user(
        self,
        user_id: uuid.UUID,
        symbol: str,
    ) -> MarketIndexDefinition | None:
        result = await self.session.execute(
            select(MarketIndexDefinition).where(
                MarketIndexDefinition.user_id == user_id,
                MarketIndexDefinition.symbol == symbol,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, definition: MarketIndexDefinition) -> MarketIndexDefinition:
        self.session.add(definition)
        await self.session.flush()
        await self.session.refresh(definition)
        return definition

    async def update(
        self,
        model: MarketIndexDefinition,
        symbol: str | None = None,
        name: str | None = None,
        tradingview_url: str | None = None,
        is_active: bool | None = None,
    ) -> MarketIndexDefinition:
        if symbol is not None:
            model.symbol = symbol
        if name is not None:
            model.name = name
        if tradingview_url is not None:
            model.tradingview_url = tradingview_url
        if is_active is not None:
            model.is_active = is_active
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def delete(self, definition: MarketIndexDefinition) -> None:
        await self.session.delete(definition)
        await self.session.flush()

    async def seed_defaults(self, user_id: uuid.UUID) -> None:
        defaults = [
            {
                "symbol": "SPX",
                "name": "S&P 500",
                "tradingview_url": "https://www.tradingview.com/symbols/SPX/",
            },
            {
                "symbol": "NDX",
                "name": "NASDAQ 100",
                "tradingview_url": "https://www.tradingview.com/symbols/NDX/",
            },
            {
                "symbol": "DAX",
                "name": "DAX",
                "tradingview_url": "https://www.tradingview.com/symbols/XETR-DAX/",
            },
        ]
        stmt = pg_insert(MarketIndexDefinition).values(
            [
                {
                    "user_id": user_id,
                    "symbol": row["symbol"],
                    "name": row["name"],
                    "tradingview_url": row["tradingview_url"],
                    "is_active": True,
                }
                for row in defaults
            ]
        )
        stmt = stmt.on_conflict_do_nothing(
            constraint="uq_market_index_user_symbol",
        )
        await self.session.execute(stmt)
        await self.session.flush()
