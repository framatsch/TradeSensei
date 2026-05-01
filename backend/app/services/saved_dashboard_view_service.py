"""Service layer for portfolio-scoped saved dashboard views."""

import uuid

from app.core.exceptions import (
    SavedDashboardViewNotFoundError,
    SavedDashboardViewPermissionError,
)
from app.models.saved_dashboard_view import SavedDashboardView
from app.repositories.portfolio_repository import PortfolioRepository
from app.repositories.saved_dashboard_view_repository import (
    SavedDashboardViewRepository,
)
from app.schemas.analytics import (
    SavedDashboardViewCreate,
    SavedDashboardViewUpdate,
)
from app.services.cache_service import CacheService


class SavedDashboardViewService:
    """Business rules for saved analytics views."""

    def __init__(
        self,
        view_repository: SavedDashboardViewRepository,
        portfolio_repository: PortfolioRepository,
        cache_service: CacheService,
    ) -> None:
        self._views = view_repository
        self._portfolios = portfolio_repository
        self._cache = cache_service

    async def _assert_portfolio_owner(
        self,
        *,
        portfolio_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        portfolio = await self._portfolios.get_by_id(portfolio_id, user_id)
        if portfolio is None:
            raise SavedDashboardViewPermissionError("portfolio does not belong to user")

    async def create_view(
        self,
        *,
        portfolio_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: SavedDashboardViewCreate,
    ) -> SavedDashboardView:
        """Create a saved dashboard view for one portfolio."""
        await self._assert_portfolio_owner(portfolio_id=portfolio_id, user_id=user_id)
        return await self._views.create(
            user_id=user_id,
            portfolio_id=portfolio_id,
            name=payload.name,
            filter_config=payload.filter_config.model_dump(by_alias=True),
        )

    async def list_views(
        self,
        *,
        portfolio_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[SavedDashboardView]:
        """List all saved views for one portfolio."""
        await self._assert_portfolio_owner(portfolio_id=portfolio_id, user_id=user_id)
        return list(
            await self._views.list_by_portfolio(
                user_id=user_id,
                portfolio_id=portfolio_id,
            )
        )

    async def get_view(
        self,
        *,
        portfolio_id: uuid.UUID,
        view_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> SavedDashboardView:
        """Return one saved view or raise if inaccessible."""
        await self._assert_portfolio_owner(portfolio_id=portfolio_id, user_id=user_id)
        view = await self._views.get_by_id(view_id)
        if view is None or view.user_id != user_id or view.portfolio_id != portfolio_id:
            raise SavedDashboardViewNotFoundError("saved dashboard view not found")
        return view

    async def update_view(
        self,
        *,
        portfolio_id: uuid.UUID,
        view_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: SavedDashboardViewUpdate,
    ) -> SavedDashboardView:
        """Update one saved view and invalidate related cache keys."""
        view = await self.get_view(
            portfolio_id=portfolio_id,
            view_id=view_id,
            user_id=user_id,
        )
        updated = await self._views.update(
            model=view,
            name=payload.name,
            filter_config=(
                payload.filter_config.model_dump(by_alias=True)
                if payload.filter_config is not None
                else None
            ),
        )
        await self._cache.invalidate_portfolio(portfolio_id, user_id)
        return updated

    async def delete_view(
        self,
        *,
        portfolio_id: uuid.UUID,
        view_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Delete one saved view and invalidate related cache keys."""
        _ = await self.get_view(
            portfolio_id=portfolio_id,
            view_id=view_id,
            user_id=user_id,
        )
        await self._views.delete(view_id)
        await self._cache.invalidate_portfolio(portfolio_id, user_id)
