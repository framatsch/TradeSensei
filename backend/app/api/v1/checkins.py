"""Route handlers for daily check-ins."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_session_with_rls
from app.core.exceptions import (
    ConfigurationError,
    DailyCheckinNotFoundError,
    DailyCheckinValidationError,
    UnsupportedContentTypeError,
)
from app.models.user import User
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
        presigned_url, public_url = service.generate_screenshot_upload_url(
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
            public_url=public_url,
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
    except DailyCheckinValidationError as exc:
        if "already exists" in str(exc):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=str(exc)
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc


@router.get(
    "",
    response_model=ResponseEnvelope[DailyCheckinListResponse],
    summary="List daily check-ins",
    description="List user check-ins with optional date filters and date cursor.",
)
async def list_checkins(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[DailyCheckinService, Depends(_get_service)],
    from_date: date | None = None,
    to_date: date | None = None,
    market_phase: str | None = None,
    cursor: date | None = None,
    limit: int = 30,
) -> ResponseEnvelope[DailyCheckinListResponse]:
    data = await service.list_checkins(
        user_id=current_user.id,
        from_date=from_date,
        to_date=to_date,
        market_phase=market_phase,
        cursor=cursor,
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
        item = await service.get_checkin(
            user_id=current_user.id, checkin_date=checkin_date
        )
        return ResponseEnvelope[DailyCheckinRead](data=item)
    except DailyCheckinNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


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
        item = await service.update_checkin(
            user_id=current_user.id, checkin_date=checkin_date, payload=payload
        )
        return ResponseEnvelope[DailyCheckinRead](data=item)
    except DailyCheckinNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except DailyCheckinValidationError as exc:
        if "already exists" in str(exc):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=str(exc)
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
