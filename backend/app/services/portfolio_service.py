"""Business-logic service for portfolio operations."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PortfolioNotFoundError, PortfolioValidationError
from app.repositories.portfolio_repository import PortfolioRepository
from app.schemas.portfolio import PortfolioCreate, PortfolioRead, PortfolioUpdate


class PortfolioService:
    """Service layer for user portfolio management."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = PortfolioRepository(session)

    async def create_portfolio(self, user_id: uuid.UUID, data: PortfolioCreate) -> PortfolioRead:
        existing = await self._repo.get_by_name(user_id, data.name)
        if existing is not None:
            raise PortfolioValidationError("Portfolio name already exists.")
        item = await self._repo.create(user_id, data)
        await self._session.commit()
        return PortfolioRead.model_validate(item)

    async def get_portfolio(self, portfolio_id: uuid.UUID, user_id: uuid.UUID) -> PortfolioRead:
        item = await self._repo.get_by_id(portfolio_id, user_id)
        if item is None:
            raise PortfolioNotFoundError("Portfolio not found.")
        return PortfolioRead.model_validate(item)

    async def list_portfolios(self, user_id: uuid.UUID) -> list[PortfolioRead]:
        items = await self._repo.list_by_user(user_id)
        return [PortfolioRead.model_validate(item) for item in items]

    async def update_portfolio(
        self,
        portfolio_id: uuid.UUID,
        user_id: uuid.UUID,
        data: PortfolioUpdate,
    ) -> PortfolioRead:
        item = await self._repo.get_by_id(portfolio_id, user_id)
        if item is None:
            raise PortfolioNotFoundError("Portfolio not found.")

        if data.name is not None and data.name != item.name:
            existing = await self._repo.get_by_name(user_id, data.name)
            if existing is not None and existing.id != item.id:
                raise PortfolioValidationError("Portfolio name already exists.")

        if data.base_currency is not None and data.base_currency != item.base_currency and await self._repo.has_trades(item.id):
            raise PortfolioValidationError("Cannot change base_currency after trades exist.")

        updated = await self._repo.update(item, data)
        await self._session.commit()
        return PortfolioRead.model_validate(updated)

    async def delete_portfolio(self, portfolio_id: uuid.UUID, user_id: uuid.UUID) -> None:
        item = await self._repo.get_by_id(portfolio_id, user_id)
        if item is None:
            raise PortfolioNotFoundError("Portfolio not found.")

        if await self._repo.has_accounts(item.id):
            raise PortfolioValidationError("Portfolio has linked accounts.")

        await self._repo.delete(item)
        await self._session.commit()
