"""Route handlers for the ``/api/v1/portfolios`` resource."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_session_with_rls
from app.core.exceptions import PortfolioNotFoundError, PortfolioValidationError
from app.models.user import User
from app.schemas.common import ResponseEnvelope
from app.schemas.portfolio import PortfolioCreate, PortfolioRead, PortfolioUpdate
from app.services.portfolio_service import PortfolioService

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


def _get_service(
    session: Annotated[AsyncSession, Depends(get_session_with_rls)],
) -> PortfolioService:
    return PortfolioService(session)


@router.get("", response_model=ResponseEnvelope[list[PortfolioRead]])
async def list_portfolios(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PortfolioService, Depends(_get_service)],
) -> ResponseEnvelope[list[PortfolioRead]]:
    items = await service.list_portfolios(current_user.id)
    return ResponseEnvelope(data=items)


@router.post(
    "",
    response_model=ResponseEnvelope[PortfolioRead],
    status_code=status.HTTP_201_CREATED,
)
async def create_portfolio(
    payload: PortfolioCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PortfolioService, Depends(_get_service)],
) -> ResponseEnvelope[PortfolioRead]:
    try:
        item = await service.create_portfolio(current_user.id, payload)
        return ResponseEnvelope(data=item)
    except PortfolioValidationError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


@router.get("/{portfolio_id}", response_model=ResponseEnvelope[PortfolioRead])
async def get_portfolio(
    portfolio_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PortfolioService, Depends(_get_service)],
) -> ResponseEnvelope[PortfolioRead]:
    try:
        item = await service.get_portfolio(portfolio_id, current_user.id)
        return ResponseEnvelope(data=item)
    except PortfolioNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.patch("/{portfolio_id}", response_model=ResponseEnvelope[PortfolioRead])
async def update_portfolio(
    portfolio_id: uuid.UUID,
    payload: PortfolioUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PortfolioService, Depends(_get_service)],
) -> ResponseEnvelope[PortfolioRead]:
    try:
        item = await service.update_portfolio(
            portfolio_id,
            current_user.id,
            payload,
        )
        return ResponseEnvelope(data=item)
    except PortfolioNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except PortfolioValidationError as e:
        # base_currency change after trades exist → 422; name conflict → 409
        status_code = status.HTTP_422_UNPROCESSABLE_CONTENT if "base_currency" in str(e) else status.HTTP_409_CONFLICT
        raise HTTPException(status_code=status_code, detail=str(e)) from e


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio(
    portfolio_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PortfolioService, Depends(_get_service)],
) -> Response:
    try:
        await service.delete_portfolio(portfolio_id, current_user.id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except PortfolioNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except PortfolioValidationError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
