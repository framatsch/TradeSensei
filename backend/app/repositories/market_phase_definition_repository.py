"""Repository for market phase definition persistence."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.daily_checkin import MarketPhaseDefinition


class MarketPhaseDefinitionRepository:
    """Data-access operations for market phase definitions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        user_id: uuid.UUID,
        name: str,
        label: str,
        color_hex: str,
    ) -> MarketPhaseDefinition:
        """Create and flush a new market phase definition."""
        model = MarketPhaseDefinition(
            user_id=user_id,
            name=name,
            label=label,
            color_hex=color_hex,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def get_by_id(
        self,
        definition_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> MarketPhaseDefinition | None:
        """Return a user-scoped phase definition by id."""
        result = await self._session.execute(
            select(MarketPhaseDefinition).where(
                MarketPhaseDefinition.id == definition_id,
                MarketPhaseDefinition.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        is_active: bool | None = None,
    ) -> Sequence[MarketPhaseDefinition]:
        """List user phase definitions ordered by creation time."""
        stmt = (
            select(MarketPhaseDefinition)
            .where(MarketPhaseDefinition.user_id == user_id)
            .order_by(MarketPhaseDefinition.created_at.asc())
        )
        if is_active is not None:
            stmt = stmt.where(MarketPhaseDefinition.is_active == is_active)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def update(
        self,
        model: MarketPhaseDefinition,
        label: str | None = None,
        color_hex: str | None = None,
        is_active: bool | None = None,
    ) -> MarketPhaseDefinition:
        """Update and flush a market phase definition."""
        if label is not None:
            model.label = label
        if color_hex is not None:
            model.color_hex = color_hex
        if is_active is not None:
            model.is_active = is_active
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def get_by_name_and_user(
        self,
        user_id: uuid.UUID,
        name: str,
    ) -> MarketPhaseDefinition | None:
        """Return a phase definition by stable name for a user."""
        result = await self._session.execute(
            select(MarketPhaseDefinition).where(
                MarketPhaseDefinition.user_id == user_id,
                MarketPhaseDefinition.name == name,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_label_and_user(
        self,
        user_id: uuid.UUID,
        label: str,
    ) -> MarketPhaseDefinition | None:
        """Return a phase definition by label for a user."""
        result = await self._session.execute(
            select(MarketPhaseDefinition).where(
                MarketPhaseDefinition.user_id == user_id,
                MarketPhaseDefinition.label == label,
            )
        )
        return result.scalar_one_or_none()

    async def delete(self, model: MarketPhaseDefinition) -> None:
        """Delete a market phase definition model."""
        await self._session.delete(model)
        await self._session.flush()

    async def seed_defaults(self, user_id: uuid.UUID) -> None:
        """Insert default phase definitions if they do not exist."""
        defaults = [
            {"name": "bullish", "label": "Bullish", "color_hex": "#22c55e"},
            {"name": "bearish", "label": "Bearish", "color_hex": "#ef4444"},
            {"name": "sideways", "label": "Sideways", "color_hex": "#f59e0b"},
            {"name": "volatile", "label": "Volatile", "color_hex": "#8b5cf6"},
        ]
        stmt = pg_insert(MarketPhaseDefinition).values(
            [
                {
                    "user_id": user_id,
                    "name": row["name"],
                    "label": row["label"],
                    "color_hex": row["color_hex"],
                    "is_active": True,
                }
                for row in defaults
            ]
        )
        stmt = stmt.on_conflict_do_nothing(
            constraint="uq_market_phase_user_name",
        )
        await self._session.execute(stmt)
        await self._session.flush()
