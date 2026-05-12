"""Repository for persisted dashboard views."""

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.saved_dashboard_view import SavedDashboardView


class SavedDashboardViewRepository:
    """Data-access operations for saved dashboard views."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID,
        name: str,
        filter_config: dict[str, Any],
    ) -> SavedDashboardView:
        """Create and flush a saved dashboard view."""
        model = SavedDashboardView(
            user_id=user_id,
            portfolio_id=portfolio_id,
            name=name,
            filter_config=filter_config,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def get_by_id(self, view_id: uuid.UUID) -> SavedDashboardView | None:
        """Fetch one saved dashboard view by ID."""
        result = await self._session.execute(select(SavedDashboardView).where(SavedDashboardView.id == view_id))
        return result.scalar_one_or_none()

    async def list_by_portfolio(
        self,
        *,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID,
    ) -> Sequence[SavedDashboardView]:
        """List views for one user-owned portfolio."""
        result = await self._session.execute(
            select(SavedDashboardView)
            .where(
                SavedDashboardView.user_id == user_id,
                SavedDashboardView.portfolio_id == portfolio_id,
            )
            .order_by(SavedDashboardView.updated_at.desc())
        )
        return result.scalars().all()

    async def update(
        self,
        *,
        model: SavedDashboardView,
        name: str | None = None,
        filter_config: dict[str, Any] | None = None,
    ) -> SavedDashboardView:
        """Update mutable fields on a saved dashboard view."""
        if name is not None:
            model.name = name
        if filter_config is not None:
            model.filter_config = filter_config
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def delete(self, view_id: uuid.UUID) -> None:
        """Delete one saved dashboard view by ID."""
        await self._session.execute(delete(SavedDashboardView).where(SavedDashboardView.id == view_id))
        await self._session.flush()
