import datetime as dt
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_session_with_rls
from app.models.user import User
from app.schemas.common import ResponseEnvelope
from app.schemas.model_book import ModelBookEntriesPage
from app.services.model_book_service import ModelBookService

router = APIRouter(prefix="/model-book", tags=["model_book"])

def _get_service(session: Annotated[AsyncSession, Depends(get_session_with_rls)]) -> ModelBookService:
    return ModelBookService(session)

@router.get("/entries", response_model=ResponseEnvelope[ModelBookEntriesPage])
async def get_model_book_entries(
    service: Annotated[ModelBookService, Depends(_get_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    entity_type: Literal["trade", "checkin", "all"] = Query("all", description="Filter by entity type"),
    from_date: dt.date | None = Query(None, description="Start date (inclusive)"),
    to_date: dt.date | None = Query(None, description="End date (inclusive)"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
) -> ResponseEnvelope[ModelBookEntriesPage]:
    """Get mixed list of starred trades and check-ins."""
    page_data = await service.get_entries(
        user_id=current_user.id,
        entity_type=entity_type,
        from_date=from_date,
        to_date=to_date,
        page=page,
        per_page=per_page,
    )
    return ResponseEnvelope[ModelBookEntriesPage](data=page_data)
