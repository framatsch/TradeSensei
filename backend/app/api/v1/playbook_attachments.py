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

"""Route handlers for playbook image attachments."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_session_with_rls
from app.core.exceptions import (
    ConfigurationError,
    PlaybookAttachmentNotFoundError,
    PlaybookNotFoundError,
    UnsupportedContentTypeError,
)
from app.models.user import User
from app.schemas.playbook_attachment import (
    PlaybookImageRegisterRequest,
    PlaybookImageResponse,
    PlaybookImageUploadRequest,
    PlaybookImageUploadUrlResponse,
)
from app.services.playbook_attachment_service import PlaybookAttachmentService

router = APIRouter(prefix="/playbooks", tags=["playbook-metadata"])


def _get_service(
    session: Annotated[AsyncSession, Depends(get_session_with_rls)],
) -> PlaybookAttachmentService:
    return PlaybookAttachmentService(session)


@router.post(
    "/{playbook_id}/attachments/upload-url",
    response_model=PlaybookImageUploadUrlResponse,
    summary="Generate presigned upload URL for playbook image",
)
async def generate_upload_url(
    playbook_id: uuid.UUID,
    payload: PlaybookImageUploadRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PlaybookAttachmentService, Depends(_get_service)],
) -> PlaybookImageUploadUrlResponse:
    """Generate a presigned PUT URL for uploading an image to a playbook."""
    try:
        return await service.generate_upload_url(
            playbook_id=playbook_id,
            user_id=current_user.id,
            filename=payload.filename,
            content_type=payload.content_type,
        )
    except PlaybookNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except UnsupportedContentTypeError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except ConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.post(
    "/{playbook_id}/attachments",
    response_model=PlaybookImageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register uploaded image as playbook attachment",
)
async def register_attachment(
    playbook_id: uuid.UUID,
    payload: PlaybookImageRegisterRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PlaybookAttachmentService, Depends(_get_service)],
) -> PlaybookImageResponse:
    """Register a previously uploaded image as an attachment on a playbook."""
    try:
        return await service.register(
            playbook_id=playbook_id,
            user_id=current_user.id,
            payload=payload,
        )
    except PlaybookNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except UnsupportedContentTypeError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.get(
    "/{playbook_id}/attachments",
    response_model=list[PlaybookImageResponse],
    summary="List images for playbook",
)
async def list_attachments(
    playbook_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PlaybookAttachmentService, Depends(_get_service)],
) -> list[PlaybookImageResponse]:
    """Return all images registered on a playbook."""
    try:
        return await service.list(playbook_id=playbook_id, user_id=current_user.id)
    except PlaybookNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete(
    "/{playbook_id}/attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete playbook image",
)
async def delete_attachment(
    playbook_id: uuid.UUID,
    attachment_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PlaybookAttachmentService, Depends(_get_service)],
) -> None:
    """Delete an image attachment from a playbook."""
    try:
        await service.delete(
            playbook_id=playbook_id,
            attachment_id=attachment_id,
            user_id=current_user.id,
        )
    except PlaybookNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PlaybookAttachmentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
