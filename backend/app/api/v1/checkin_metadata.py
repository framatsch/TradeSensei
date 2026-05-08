"""Route handlers for check-in taxonomy and annotation assignments."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_session_with_rls
from app.core.exceptions import (
    DailyCheckinNotFoundError,
    MetadataAssignmentNotFoundError,
    MetadataAssignmentValidationError,
    TaxonomyNotFoundError,
)
from app.models.user import User
from app.schemas.annotation_definition import AnnotationAssignRequest
from app.schemas.taxonomy import TaxonomyAssignRequest
from app.services.checkin_metadata_service import CheckinMetadataService

router = APIRouter(prefix="/checkins", tags=["checkin-metadata"])


def _get_service(
    session: Annotated[AsyncSession, Depends(get_session_with_rls)],
) -> CheckinMetadataService:
    """Build check-in metadata service from request session."""
    return CheckinMetadataService(session)


@router.post(
    "/{checkin_id}/taxonomies",
    status_code=status.HTTP_201_CREATED,
    summary="Assign taxonomy to check-in",
)
async def assign_checkin_taxonomy(
    checkin_id: uuid.UUID,
    payload: TaxonomyAssignRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CheckinMetadataService, Depends(_get_service)],
) -> None:
    """Assign one taxonomy definition to a check-in."""
    try:
        await service.assign_taxonomy(checkin_id, payload.taxonomy_id, current_user.id)
    except DailyCheckinNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TaxonomyNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MetadataAssignmentValidationError as exc:
        status_code = status.HTTP_409_CONFLICT if "already assigned" in str(exc) else status.HTTP_422_UNPROCESSABLE_CONTENT
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.delete(
    "/{checkin_id}/taxonomies/{taxonomy_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove taxonomy from check-in",
)
async def remove_checkin_taxonomy(
    checkin_id: uuid.UUID,
    taxonomy_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CheckinMetadataService, Depends(_get_service)],
) -> None:
    """Remove taxonomy assignment from a check-in."""
    try:
        await service.remove_taxonomy(checkin_id, taxonomy_id, current_user.id)
    except DailyCheckinNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MetadataAssignmentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/{checkin_id}/annotations/{annotation_definition_id}",
    status_code=status.HTTP_201_CREATED,
    summary="Assign annotation to check-in",
)
async def assign_checkin_annotation(
    checkin_id: uuid.UUID,
    annotation_definition_id: uuid.UUID,
    payload: AnnotationAssignRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CheckinMetadataService, Depends(_get_service)],
) -> None:
    """Assign one annotation definition to a check-in with a typed value."""
    try:
        await service.assign_annotation(
            checkin_id,
            annotation_definition_id,
            payload.value,
            current_user.id,
        )
    except DailyCheckinNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MetadataAssignmentValidationError as exc:
        status_code = status.HTTP_409_CONFLICT if "already assigned" in str(exc) else status.HTTP_422_UNPROCESSABLE_CONTENT
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.put(
    "/{checkin_id}/annotations/{annotation_definition_id}",
    status_code=status.HTTP_200_OK,
    summary="Update annotation on check-in",
)
async def update_checkin_annotation(
    checkin_id: uuid.UUID,
    annotation_definition_id: uuid.UUID,
    payload: AnnotationAssignRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CheckinMetadataService, Depends(_get_service)],
) -> None:
    """Update annotation value on a check-in assignment."""
    try:
        await service.update_annotation(
            checkin_id,
            annotation_definition_id,
            payload.value,
            current_user.id,
        )
    except DailyCheckinNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MetadataAssignmentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MetadataAssignmentValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.delete(
    "/{checkin_id}/annotations/{annotation_definition_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove annotation from check-in",
)
async def remove_checkin_annotation(
    checkin_id: uuid.UUID,
    annotation_definition_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CheckinMetadataService, Depends(_get_service)],
) -> None:
    """Remove annotation assignment from a check-in."""
    try:
        await service.remove_annotation(
            checkin_id,
            annotation_definition_id,
            current_user.id,
        )
    except DailyCheckinNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MetadataAssignmentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
