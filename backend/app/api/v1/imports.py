"""Route handlers for the broker file import endpoint.

Accepts multipart file uploads and delegates to
:class:`~app.services.import_service.ImportService` for parsing and
persisting trades.
"""

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import IMPORT_MAX_FILE_SIZE_MB, IMPORT_SUPPORTED_FORMATS
from app.core.database import get_session
from app.core.deps import get_current_user
from app.core.exceptions import (
    AccountNotFoundError,
    ImportParseError,
    UnsupportedBrokerError,
)
from app.models.user import User
from app.schemas.common import ResponseEnvelope
from app.schemas.imports import ImportResult
from app.services.import_service import ImportService
from app.utils.parsers.factory import BrokerType

router = APIRouter(prefix="/imports", tags=["imports"])

# 1 MB in bytes.
_BYTES_PER_MB: int = 1024 * 1024


def _get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ImportService:
    """FastAPI dependency that constructs an :class:`ImportService`.

    Args:
        session: Injected async database session.

    Returns:
        An :class:`ImportService` bound to the current session.
    """
    return ImportService(session)


@router.post(
    "/upload",
    response_model=ResponseEnvelope[ImportResult],
    status_code=status.HTTP_200_OK,
    summary="Upload a broker export file and import trades",
    description=(
        "Parse a broker export file (CSV or XLSX) and bulk-create the "
        "contained trades for the specified account. "
        "Supported brokers: `ibkr` (Interactive Brokers Activity Statement CSV), "
        "`schwab` (Charles Schwab trade history CSV). "
        f"Maximum file size: {IMPORT_MAX_FILE_SIZE_MB} MB. "
        f"Accepted formats: {', '.join(IMPORT_SUPPORTED_FORMATS)}."
    ),
    response_description=(
        "A summary of the import operation wrapped in a response envelope, "
        "including the number of trades created and any parse warnings."
    ),
    responses={
        200: {"description": "Import completed. Check warnings for skipped rows."},
        400: {"description": "File format not supported or parse error."},
        401: {"description": "Authentication required."},
        404: {"description": "Account not found or not owned by the current user."},
        413: {"description": "File exceeds the maximum allowed size."},
        422: {"description": "Form parameter validation error."},
    },
)
async def upload_import(
    service: Annotated[ImportService, Depends(_get_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    broker: Annotated[
        BrokerType,
        Form(description="Broker type: 'ibkr' or 'schwab'."),
    ],
    file: UploadFile,
    account_id: Annotated[
        Optional[uuid.UUID],
        Form(description="UUID of the account to import trades into (optional)."),
    ] = None,
) -> ResponseEnvelope[ImportResult]:
    """Upload a broker export file and import the trades it contains.

    Args:
        service: Injected import service.
        current_user: The authenticated user (account ownership is
            validated inside the service).
        broker: The broker type that determines which parser to use.
        account_id: UUID of the target broker account.
        file: The uploaded file (CSV or XLSX).

    Returns:
        A :class:`~app.schemas.common.ResponseEnvelope` wrapping an
        :class:`~app.schemas.imports.ImportResult` with counts and
        any non-fatal warnings.

    Raises:
        HTTPException: 400 if the file extension is not supported or the
            file cannot be parsed.
        HTTPException: 404 if the account is not found or not owned by
            the current user.
        HTTPException: 413 if the uploaded file exceeds the size limit.
    """
    # --- Validate file extension -------------------------------------------
    filename = file.filename or "upload"
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in IMPORT_SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file format '.{extension}'. "
                f"Accepted formats: {', '.join(IMPORT_SUPPORTED_FORMATS)}."
            ),
        )

    # --- Read file content with size guard ---------------------------------
    max_bytes = IMPORT_MAX_FILE_SIZE_MB * _BYTES_PER_MB
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"File exceeds the maximum allowed size of "
                f"{IMPORT_MAX_FILE_SIZE_MB} MB."
            ),
        )

    # --- Delegate to service -----------------------------------------------
    try:
        result = await service.import_file(
            content=content,
            filename=filename,
            broker=broker,
            account_id=account_id,
            user_id=current_user.id,
        )
    except AccountNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (ImportParseError, UnsupportedBrokerError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return ResponseEnvelope[ImportResult](data=result)
