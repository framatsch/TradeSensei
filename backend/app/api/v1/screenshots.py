"""Route handlers for screenshot upload/delete on trades.

Files are stored under ``uploads/screenshots/<trade_id>/`` inside the
configured UPLOAD_DIR and the URL path is appended to / removed from
``trade.screenshots`` (JSONB list).
"""

import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.core.deps import get_current_user
from app.core.exceptions import TradeNotFoundError
from app.models.user import User
from app.schemas.common import ResponseEnvelope
from app.schemas.trade import TradeRead
from app.services.trade_service import TradeService

router = APIRouter(prefix="/trades/{trade_id}/screenshots", tags=["screenshots"])

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


def _get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TradeService:
    return TradeService(session)


def _upload_dir(trade_id: uuid.UUID) -> Path:
    base = Path(settings.upload_dir) / "screenshots" / str(trade_id)
    base.mkdir(parents=True, exist_ok=True)
    return base


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
    """Upload a screenshot and append its URL to trade.screenshots.

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
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file type: {file.content_type}. "
                "Allowed: jpeg, png, gif, webp."
            ),
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size is 20 MB.",
        )

    # Build a safe unique filename
    suffix = Path(file.filename or "upload").suffix.lower() or ".jpg"
    filename = f"{uuid.uuid4()}{suffix}"
    dest = _upload_dir(trade_id) / filename
    dest.write_bytes(content)

    # URL path that the static files mount exposes
    url = f"/uploads/screenshots/{trade_id}/{filename}"

    try:
        trade = await service.get_trade(trade_id)
    except TradeNotFoundError as exc:
        dest.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trade not found."
        ) from exc

    from app.schemas.trade import TradeUpdate  # local import to avoid circular

    current_screenshots: list[str] = list(trade.screenshots or [])
    current_screenshots.append(url)
    updated = await service.update_trade(
        trade_id, TradeUpdate(screenshots=current_screenshots)
    )
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
    """Delete a screenshot file and remove its URL from trade.screenshots.

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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename."
        )

    try:
        trade = await service.get_trade(trade_id)
    except TradeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trade not found."
        ) from exc

    url = f"/uploads/screenshots/{trade_id}/{filename}"
    remaining = [s for s in (trade.screenshots or []) if s != url]

    # Delete file from disk
    file_path = _upload_dir(trade_id) / filename
    file_path.unlink(missing_ok=True)

    from app.schemas.trade import TradeUpdate  # local import to avoid circular

    updated = await service.update_trade(trade_id, TradeUpdate(screenshots=remaining))
    return ResponseEnvelope[TradeRead](data=updated)
