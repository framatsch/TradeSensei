"""Route handlers for screenshot upload/delete on trades.

Files are stored under ``uploads/screenshots/<trade_id>/`` inside the
configured UPLOAD_DIR and the URL path is appended to / removed from
``trade.image_urls``.
"""

import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import BYTES_PER_MB, SCREENSHOT_MAX_FILE_SIZE_MB
from app.core.deps import get_current_user, get_session_with_rls
from app.core.exceptions import TradeNotFoundError
from app.models.user import User
from app.schemas.common import ResponseEnvelope
from app.schemas.trade import TradeRead
from app.services.trade_service import TradeService

router = APIRouter(prefix="/trades/{trade_id}/screenshots", tags=["screenshots"])

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_FILE_SIZE = SCREENSHOT_MAX_FILE_SIZE_MB * BYTES_PER_MB


def _get_service(
    session: Annotated[AsyncSession, Depends(get_session_with_rls)],
) -> TradeService:
    return TradeService(session)


@router.post(
    "",
    response_model=ResponseEnvelope[TradeRead],
    status_code=status.HTTP_201_CREATED,
    summary="Upload a screenshot",
    description="Upload an image file and attach it to the trade.",
)
async def upload_screenshot(
    trade_id: uuid.UUID,
    file: UploadFile,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TradeService, Depends(_get_service)],
) -> ResponseEnvelope[TradeRead]:
    """Upload a screenshot and append its URL to trade.image_urls.

    Args:
        trade_id: UUID path parameter identifying the parent trade.
        file: The uploaded image file (multipart/form-data).
        current_user: Injected authenticated user.
        service: Injected trade service.

    Returns:
        Updated :class:`TradeRead` wrapped in a response envelope.

    Raises:
        HTTPException: 400 if file type is not allowed or file is too large.
        HTTPException: 404 if trade not found.
    """
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported file type: {file.content_type}. "
                "Allowed: jpeg, png, gif, webp."
            ),
        )

    content = await file.read()
    suffix = Path(file.filename or "upload").suffix.lower() or ".jpg"
    try:
        updated = await service.add_screenshot(trade_id, content, suffix, current_user.id)
    except ValueError as exc:
        if "File too large" in str(exc):
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=str(exc),
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except TradeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trade not found.") from exc
    return ResponseEnvelope[TradeRead](data=updated)


@router.delete(
    "/{filename}",
    response_model=ResponseEnvelope[TradeRead],
    summary="Delete a screenshot",
    description="Remove a screenshot from the trade and delete the file.",
)
async def delete_screenshot(
    trade_id: uuid.UUID,
    filename: str,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TradeService, Depends(_get_service)],
) -> ResponseEnvelope[TradeRead]:
    """Delete a screenshot file and remove its URL from trade.image_urls.

    Args:
        trade_id: UUID path parameter identifying the parent trade.
        filename: The filename of the screenshot to delete.
        current_user: Injected authenticated user.
        service: Injected trade service.

    Returns:
        Updated :class:`TradeRead` wrapped in a response envelope.

    Raises:
        HTTPException: 404 if trade not found.
    """
    # Sanitize: filename must not contain path traversal
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename.")

    try:
        trade = await service.get_trade(trade_id, current_user.id)
    except TradeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trade not found.") from exc

    # Find the URL that ends with the filename
    target_url = next(
        (s for s in (trade.image_urls or []) if s.endswith(f"/{filename}")), None
    )
    if not target_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Screenshot not found on trade.",
        )

    remaining = [s for s in (trade.image_urls or []) if s != target_url]

    from app.services.storage_service import StorageService

    storage = StorageService()
    import contextlib

    with contextlib.suppress(Exception):
        storage.delete_file_by_url(target_url)

    from app.schemas.trade import TradeUpdate  # local import to avoid circular

    updated = await service.update_trade(
        trade_id,
        TradeUpdate(image_urls=remaining),
        current_user.id,
        trade.portfolio_id,
    )
    return ResponseEnvelope[TradeRead](data=updated)
