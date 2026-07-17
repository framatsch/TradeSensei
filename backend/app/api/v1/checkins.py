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

"""Route handlers for daily check-ins."""

import json
import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_session_with_rls
from app.core.exceptions import (
    ConfigurationError,
    DailyCheckinAlreadyExistsError,
    DailyCheckinNotFoundError,
    DailyCheckinValidationError,
    UnsupportedContentTypeError,
)
from app.models.user import User
from app.schemas.annotation_filter import AnnotationFilterItem
from app.schemas.common import ResponseEnvelope
from app.schemas.daily_checkin import (
    DailyCheckinCreate,
    DailyCheckinListResponse,
    DailyCheckinRead,
    DailyCheckinUpdate,
    ScreenshotUploadUrlRequest,
    ScreenshotUploadUrlResponse,
)
from app.services.daily_checkin_service import DailyCheckinService
from app.services.storage_service import StorageService

router = APIRouter(prefix="/checkins", tags=["checkins"])


def _get_service(
    session: Annotated[AsyncSession, Depends(get_session_with_rls)],
) -> DailyCheckinService:
    return DailyCheckinService(session)


def _parse_uuid_list(raw: str | None, param_name: str) -> list[uuid.UUID] | None:
    """Parse a comma-separated string of UUIDs into a list."""
    if not raw:
        return None
    try:
        return [uuid.UUID(tid.strip()) for tid in raw.split(",") if tid.strip()]
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid {param_name} format — expected comma-separated UUIDs.",
        ) from exc


def _parse_taxonomy_ids(raw: str | None) -> list[uuid.UUID] | None:
    return _parse_uuid_list(raw, "taxonomy_ids")


def _parse_target_indices(raw: str | None) -> list[uuid.UUID] | None:
    return _parse_uuid_list(raw, "target_indices")


def _parse_annotation_filters(raw: str | None) -> list[AnnotationFilterItem] | None:
    """Parse a JSON-encoded list of AnnotationFilterItem dicts."""
    if not raw:
        return None
    try:
        items = json.loads(raw)
        return [AnnotationFilterItem.model_validate(item) for item in items]
    except (ValueError, KeyError, TypeError, ValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid annotation_filters format — expected JSON array of filter objects.",
        ) from exc


@router.post(
    "/screenshot-upload-url",
    response_model=ResponseEnvelope[ScreenshotUploadUrlResponse],
    summary="Generate screenshot upload URL",
    description="Generate a presigned URL for direct screenshot upload.",
)
async def generate_screenshot_upload_url(
    payload: ScreenshotUploadUrlRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> ResponseEnvelope[ScreenshotUploadUrlResponse]:
    service = StorageService()
    try:
        presigned_url, key = service.generate_screenshot_upload_url(
            user_id=current_user.id,
            filename=payload.filename,
            content_type=payload.content_type,
        )
    except UnsupportedContentTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except ConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return ResponseEnvelope[ScreenshotUploadUrlResponse](
        data=ScreenshotUploadUrlResponse(
            presigned_url=presigned_url,
            key=key,
        )
    )


@router.post(
    "",
    response_model=ResponseEnvelope[DailyCheckinRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create daily check-in",
    description="Create a user-scoped daily check-in entry for a date.",
)
async def create_checkin(
    payload: DailyCheckinCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[DailyCheckinService, Depends(_get_service)],
) -> ResponseEnvelope[DailyCheckinRead]:
    try:
        item = await service.create_checkin(user_id=current_user.id, payload=payload)
        return ResponseEnvelope[DailyCheckinRead](data=item)
    except DailyCheckinAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=exc.args[0] if exc.args else str(exc),
        ) from exc
    except DailyCheckinValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=exc.args[0] if exc.args else str(exc),
        ) from exc


@router.get(
    "",
    response_model=ResponseEnvelope[DailyCheckinListResponse],
    summary="List daily check-ins",
    description="List user check-ins with optional date, taxonomy, and annotation filters.",
)
async def list_checkins(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[DailyCheckinService, Depends(_get_service)],
    from_date: Annotated[date | None, Query(description="Start date (YYYY-MM-DD).")] = None,
    to_date: Annotated[date | None, Query(description="End date (YYYY-MM-DD).")] = None,
    target_indices: str | None = Query(None, description="Comma-separated list of target index UUIDs to filter by."),
    taxonomy_ids: str | None = Query(None, description="Comma-separated taxonomy UUIDs (OR logic across selected tags)."),
    annotation_filters: str | None = Query(None, description="JSON-encoded list of AnnotationFilterItem objects."),
    has_media: bool | None = Query(None, description="Filter for check-ins with media."),
    cursor: date | None = None,
    offset: int | None = Query(None, description="Numeric offset for pagination."),
    limit: int = 30,
) -> ResponseEnvelope[DailyCheckinListResponse]:
    if cursor is not None and offset is not None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Provide 'cursor' or 'offset', not both.")
    target_indices_list = _parse_target_indices(target_indices)
    taxonomy_ids_list = _parse_taxonomy_ids(taxonomy_ids)
    annotation_filters_list = _parse_annotation_filters(annotation_filters)

    data = await service.list_checkins(
        user_id=current_user.id,
        from_date=from_date,
        to_date=to_date,
        target_indices=target_indices_list,
        taxonomy_ids=taxonomy_ids_list,
        annotation_filters=annotation_filters_list,
        has_media=has_media,
        cursor=cursor,
        offset=offset,
        limit=limit,
    )
    return ResponseEnvelope[DailyCheckinListResponse](data=data)


@router.get(
    "/{checkin_date}",
    response_model=ResponseEnvelope[DailyCheckinRead],
    summary="Get daily check-in",
    description="Get one daily check-in by date.",
)
async def get_checkin(
    checkin_date: date,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[DailyCheckinService, Depends(_get_service)],
) -> ResponseEnvelope[DailyCheckinRead]:
    try:
        item = await service.get_checkin(user_id=current_user.id, checkin_date=checkin_date)
        return ResponseEnvelope[DailyCheckinRead](data=item)
    except DailyCheckinNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch(
    "/{checkin_date}",
    response_model=ResponseEnvelope[DailyCheckinRead],
    summary="Update daily check-in",
    description="Partially update one daily check-in by date.",
)
async def update_checkin(
    checkin_date: date,
    payload: DailyCheckinUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[DailyCheckinService, Depends(_get_service)],
) -> ResponseEnvelope[DailyCheckinRead]:
    try:
        item = await service.update_checkin(user_id=current_user.id, checkin_date=checkin_date, payload=payload)
        return ResponseEnvelope[DailyCheckinRead](data=item)
    except DailyCheckinNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DailyCheckinAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=exc.args[0] if exc.args else str(exc),
        ) from exc
    except DailyCheckinValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=exc.args[0] if exc.args else str(exc),
        ) from exc


@router.delete(
    "/{checkin_date}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete daily check-in",
    description="Delete one daily check-in by date.",
)
async def delete_checkin(
    checkin_date: date,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[DailyCheckinService, Depends(_get_service)],
) -> None:
    try:
        await service.delete_checkin(user_id=current_user.id, checkin_date=checkin_date)
    except DailyCheckinNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
