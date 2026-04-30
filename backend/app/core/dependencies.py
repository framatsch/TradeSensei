"""Additional FastAPI dependencies for portfolio-scoped endpoints."""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_session_with_rls
from app.models.portfolio import Portfolio
from app.models.user import User
from app.repositories.portfolio_repository import PortfolioRepository


async def get_portfolio_or_404(
    portfolio_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> Portfolio:
    """Return a portfolio owned by user or raise 404."""
    portfolio = await PortfolioRepository(db).get_by_id(portfolio_id, user_id)
    if portfolio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found.",
        )
    return portfolio


async def require_portfolio_owner(
    portfolio_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_session_with_rls)],
) -> None:
    """Ensure path portfolio belongs to current user."""
    await get_portfolio_or_404(portfolio_id, current_user.id, db)
