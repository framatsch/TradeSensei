"""Route handlers for trade taxonomy and annotation assignments."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_session_with_rls
from app.core.exceptions import (
    MetadataAssignmentNotFoundError,
    MetadataAssignmentValidationError,
    TaxonomyNotFoundError,
    TradeNotFoundError,
)
from app.models.user import User
from app.schemas.annotation_definition import AnnotationAssignRequest
from app.schemas.taxonomy import TaxonomyAssignRequest
from app.services.trade_metadata_service import TradeMetadataService

router = APIRouter(prefix="/trades", tags=["trade-metadata"])


def _get_service(
    session: Annotated[AsyncSession, Depends(get_session_with_rls)],
) -> TradeMetadataService:
    """Build trade metadata service from request session."""
    return TradeMetadataService(session)


@router.post(
    "/{trade_id}/taxonomies",
    status_code=status.HTTP_201_CREATED,
    summary="Assign taxonomy to trade",
)
async def assign_trade_taxonomy(
    trade_id: uuid.UUID,
    payload: TaxonomyAssignRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TradeMetadataService, Depends(_get_service)],
) -> None:
    """Assign one taxonomy definition to a trade."""
    try:
        await service.assign_taxonomy(trade_id, payload.taxonomy_id, current_user.id)
    except TradeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TaxonomyNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MetadataAssignmentValidationError as exc:
        status_code = status.HTTP_409_CONFLICT if "already assigned" in str(exc) else status.HTTP_422_UNPROCESSABLE_CONTENT
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.delete(
    "/{trade_id}/taxonomies/{taxonomy_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove taxonomy from trade",
)
async def remove_trade_taxonomy(
    trade_id: uuid.UUID,
    taxonomy_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TradeMetadataService, Depends(_get_service)],
) -> None:
    """Remove taxonomy assignment from a trade."""
    try:
        await service.remove_taxonomy(trade_id, taxonomy_id, current_user.id)
    except TradeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MetadataAssignmentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/{trade_id}/annotations/{annotation_definition_id}",
    status_code=status.HTTP_201_CREATED,
    summary="Assign annotation to trade",
)
async def assign_trade_annotation(
    trade_id: uuid.UUID,
    annotation_definition_id: uuid.UUID,
    payload: AnnotationAssignRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TradeMetadataService, Depends(_get_service)],
) -> None:
    """Assign one annotation definition to a trade with a typed value."""
    try:
        await service.assign_annotation(
            trade_id,
            annotation_definition_id,
            payload.value,
            current_user.id,
        )
    except TradeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MetadataAssignmentValidationError as exc:
        status_code = status.HTTP_409_CONFLICT if "already assigned" in str(exc) else status.HTTP_422_UNPROCESSABLE_CONTENT
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.put(
    "/{trade_id}/annotations/{annotation_definition_id}",
    status_code=status.HTTP_200_OK,
    summary="Update annotation on trade",
)
async def update_trade_annotation(
    trade_id: uuid.UUID,
    annotation_definition_id: uuid.UUID,
    payload: AnnotationAssignRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TradeMetadataService, Depends(_get_service)],
) -> None:
    """Update annotation value on a trade assignment."""
    try:
        await service.update_annotation(
            trade_id,
            annotation_definition_id,
            payload.value,
            current_user.id,
        )
    except TradeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MetadataAssignmentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MetadataAssignmentValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.delete(
    "/{trade_id}/annotations/{annotation_definition_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove annotation from trade",
)
async def remove_trade_annotation(
    trade_id: uuid.UUID,
    annotation_definition_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TradeMetadataService, Depends(_get_service)],
) -> None:
    """Remove annotation assignment from a trade."""
    try:
        await service.remove_annotation(
            trade_id,
            annotation_definition_id,
            current_user.id,
        )
    except TradeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MetadataAssignmentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
