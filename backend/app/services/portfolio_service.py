"""Business-logic service for portfolio operations."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.portfolio_repository import PortfolioRepository
from app.schemas.portfolio import PortfolioCreate, PortfolioRead, PortfolioUpdate


class PortfolioService:
    """Service layer for user portfolio management."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = PortfolioRepository(session)

    async def create_portfolio(
        self, db: AsyncSession, user_id: uuid.UUID, data: PortfolioCreate
    ) -> PortfolioRead:
        del db
        existing = await self._repo.get_by_name(user_id, data.name)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Portfolio name already exists.",
            )
        item = await self._repo.create(user_id, data)
        await self._session.commit()
        return PortfolioRead.model_validate(item)

    async def get_portfolio(
        self, db: AsyncSession, portfolio_id: uuid.UUID, user_id: uuid.UUID
    ) -> PortfolioRead:
        del db
        item = await self._repo.get_by_id(portfolio_id, user_id)
        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found.",
            )
        return PortfolioRead.model_validate(item)

    async def list_portfolios(
        self, db: AsyncSession, user_id: uuid.UUID
    ) -> list[PortfolioRead]:
        del db
        items = await self._repo.list_by_user(user_id)
        return [PortfolioRead.model_validate(item) for item in items]

    async def update_portfolio(
        self,
        db: AsyncSession,
        portfolio_id: uuid.UUID,
        user_id: uuid.UUID,
        data: PortfolioUpdate,
    ) -> PortfolioRead:
        del db
        item = await self._repo.get_by_id(portfolio_id, user_id)
        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found.",
            )

        if data.name is not None and data.name != item.name:
            existing = await self._repo.get_by_name(user_id, data.name)
            if existing is not None and existing.id != item.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Portfolio name already exists.",
                )

        if (
            data.base_currency is not None
            and data.base_currency != item.base_currency
            and await self._repo.has_trades(item.id)
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Cannot change base_currency after trades exist.",
            )

        updated = await self._repo.update(item, data)
        await self._session.commit()
        return PortfolioRead.model_validate(updated)

    async def delete_portfolio(
        self, db: AsyncSession, portfolio_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        del db
        item = await self._repo.get_by_id(portfolio_id, user_id)
        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found.",
            )

        if await self._repo.has_accounts(item.id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Portfolio has linked accounts.",
            )

        await self._repo.delete(item)
        await self._session.commit()
