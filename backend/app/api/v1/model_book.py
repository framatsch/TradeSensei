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
    entity_type: Annotated[Literal["trade", "checkin", "all"], Query(description="Filter by entity type")] = "all",
    from_date: Annotated[dt.date | None, Query(description="Start date (inclusive)")] = None,
    to_date: Annotated[dt.date | None, Query(description="End date (inclusive)")] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    per_page: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
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
