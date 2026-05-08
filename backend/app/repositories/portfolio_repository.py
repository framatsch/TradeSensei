"""Async repository for the ``portfolios`` table."""

import uuid

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.portfolio import Portfolio
from app.models.trade import Trade
from app.schemas.portfolio import PortfolioCreate, PortfolioUpdate


class PortfolioRepository:
    """Data-access object for user portfolios."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(
        self,
        portfolio_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Portfolio | None:
        result = await self._session.execute(
            select(Portfolio).where(
                Portfolio.id == portfolio_id,
                Portfolio.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, user_id: uuid.UUID, name: str) -> Portfolio | None:
        result = await self._session.execute(
            select(Portfolio).where(
                Portfolio.user_id == user_id,
                Portfolio.name == name,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: uuid.UUID) -> list[Portfolio]:
        result = await self._session.execute(select(Portfolio).where(Portfolio.user_id == user_id).order_by(Portfolio.created_at.asc()))
        return list(result.scalars().all())

    async def create(self, user_id: uuid.UUID, data: PortfolioCreate) -> Portfolio:
        item = Portfolio(
            user_id=user_id,
            name=data.name,
            base_currency=data.base_currency,
            color_hex=data.color_hex,
        )
        self._session.add(item)
        await self._session.flush()
        await self._session.refresh(item)
        return item

    async def update(self, portfolio: Portfolio, data: PortfolioUpdate) -> Portfolio:
        payload = data.model_dump(exclude_unset=True)
        for field, value in payload.items():
            setattr(portfolio, field, value)
        self._session.add(portfolio)
        await self._session.flush()
        await self._session.refresh(portfolio)
        return portfolio

    async def delete(self, portfolio: Portfolio) -> None:
        await self._session.delete(portfolio)
        await self._session.flush()

    async def has_trades(self, portfolio_id: uuid.UUID) -> bool:
        stmt = select(
            exists().where(
                Trade.account_id == Account.id,
                Account.portfolio_id == portfolio_id,
            )
        )
        result = await self._session.execute(stmt)
        return bool(result.scalar())

    async def has_accounts(self, portfolio_id: uuid.UUID) -> bool:
        stmt = select(exists().where(Account.portfolio_id == portfolio_id))
        result = await self._session.execute(stmt)
        return bool(result.scalar())
