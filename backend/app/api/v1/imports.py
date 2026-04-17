"""Route handlers for the broker file import endpoint.

Accepts multipart file uploads and delegates to
:class:`~app.services.import_service.ImportService` for parsing and
persisting trades.  Also exposes an IBKR Flex Query automatic import
endpoint backed by :class:`~app.services.flex_import_service.FlexImportService`.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query, UploadFile, status
from fastapi import Form as FastAPIForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import IMPORT_MAX_FILE_SIZE_MB, IMPORT_SUPPORTED_FORMATS
from app.core.deps import get_current_user, get_session_with_rls
from app.core.exceptions import (
    AccountNotFoundError,
    BrokerRawTransactionNotFoundError,
    FlexAPIError,
    ImportParseError,
    RateLimitError,
    UnsupportedBrokerError,
)
from app.models.user import User
from app.schemas.broker_raw_transaction import BrokerRawTransactionRead
from app.schemas.common import ResponseEnvelope
from app.schemas.imports import FlexImportRequest, FreshStartResult, ImportResult
from app.services.flex_import_service import FlexImportService
from app.services.import_service import ImportService
from app.utils.parsers.factory import BrokerType

router = APIRouter(prefix="/imports", tags=["imports"])

# 1 MB in bytes.
_BYTES_PER_MB: int = 1024 * 1024


def _get_service(
    session: Annotated[AsyncSession, Depends(get_session_with_rls)],
) -> ImportService:
    """FastAPI dependency that constructs an :class:`ImportService`.

    Args:
        session: Injected async database session.

    Returns:
        An :class:`ImportService` bound to the current session.
    """
    return ImportService(session)


def _get_flex_service(
    session: Annotated[AsyncSession, Depends(get_session_with_rls)],
) -> FlexImportService:
    """FastAPI dependency that constructs a :class:`FlexImportService`.

    Args:
        session: Injected async database session.

    Returns:
        A :class:`FlexImportService` bound to the current session.

    Raises:
        HTTPException: 503 if ``IBKR_FLEX_TOKEN`` is not configured.
    """
    token = settings.ibkr_flex_token
    if not token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "IBKR Flex import is not configured on this server. "
                "Set the IBKR_FLEX_TOKEN environment variable to enable it."
            ),
        )
    return FlexImportService(session, flex_token=token)


@router.post(
    "/upload",
    response_model=ResponseEnvelope[ImportResult],
    status_code=status.HTTP_200_OK,
    summary="Upload a broker export file and import trades",
    description=(
        "Parse a broker export file (CSV, XLSX, or XML) and bulk-create the "
        "contained trades for the specified account. "
        "Supported brokers: `ibkr` (Interactive Brokers Activity Statement CSV "
        "or Flex Query XML), "
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
        FastAPIForm(description="Broker type: 'ibkr' or 'schwab'."),
    ],
    file: UploadFile,
    account_id: Annotated[
        uuid.UUID | None,
        FastAPIForm(
            description="UUID of the account to import trades into (optional)."
        ),
    ] = None,
    overwrite_manually_edited: Annotated[
        bool,
        FastAPIForm(
            description=(
                "When true, trades that have been manually edited are no longer "
                "protected and will be overwritten by the incoming import data. "
                "Defaults to false."
            )
        ),
    ] = False,
) -> ResponseEnvelope[ImportResult]:
    """Upload a broker export file and import the trades it contains.

    Args:
        service: Injected import service.
        current_user: The authenticated user (account ownership is
            validated inside the service).
        broker: The broker type that determines which parser to use.
        account_id: UUID of the target broker account.
        file: The uploaded file (CSV, XLSX, or XML).
        overwrite_manually_edited: When ``True``, manually-edited trades
            are overwritten instead of skipped.

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

    # --- Route XML uploads for IBKR to the Flex/XML parser -----------------
    # IBKR Activity Flex Query exports are XML files.  The user selects
    # broker="ibkr" in the UI; we transparently switch to ibkr_flex so the
    # IBKRXMLParser handles the file instead of the CSV parser.
    effective_broker = broker
    if extension == "xml" and broker == BrokerType.IBKR:
        effective_broker = BrokerType.IBKR_FLEX

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
            broker=effective_broker,
            account_id=account_id,
            user_id=current_user.id,
            overwrite_manually_edited=overwrite_manually_edited,
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


@router.post(
    "/{account_id}/fresh-start",
    response_model=ResponseEnvelope[FreshStartResult],
    status_code=status.HTTP_200_OK,
    summary="Fresh-start: reset account and re-import from scratch",
    description=(
        "Destructive operation — deletes ALL ``LogicalExecution`` and ``Trade`` rows "
        "for the specified account, then processes the uploaded file. "
        "BrokerRawTransactions are never deleted. "
        "Suppressed BRTs remain suppressed and are skipped during re-import. "
        "The entire operation runs in a single DB transaction — any error rolls "
        "back all changes."
    ),
    responses={
        200: {"description": "Fresh-start completed. Check import_result for details."},
        400: {"description": "File format not supported or parse error."},
        401: {"description": "Authentication required."},
        404: {"description": "Account not found or not owned by the current user."},
        413: {"description": "File exceeds the maximum allowed size."},
    },
)
async def fresh_start_import(
    account_id: uuid.UUID,
    service: Annotated[ImportService, Depends(_get_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    broker: Annotated[
        BrokerType,
        FastAPIForm(description="Broker type: 'ibkr' or 'schwab'."),
    ],
    file: UploadFile,
    acknowledged: Annotated[
        bool,
        FastAPIForm(
            description=(
                "Must be true to confirm that all trades and executions "
                "for this account will be deleted before re-importing."
            )
        ),
    ] = False,
) -> ResponseEnvelope[FreshStartResult]:
    """Reset an account and re-import all trades from a broker file.

    Args:
        account_id: UUID of the account to reset.
        service: Injected import service.
        current_user: The authenticated user.
        broker: The broker type that determines which parser to use.
        file: The uploaded broker export file.
        acknowledged: Must be True to confirm the destructive action.

    Returns:
        A fresh-start result with delete counts and the import result.

    Raises:
        HTTPException: 400 if ``acknowledged`` is False or the file cannot be parsed.
        HTTPException: 404 if the account is not found.
        HTTPException: 413 if the file is too large.
    """
    if not acknowledged:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Please set acknowledged=true to confirm that all trades and "
                "executions for this account will be deleted before re-importing."
            ),
        )

    # --- Validate file extension ---
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

    effective_broker = broker
    if extension == "xml" and broker == BrokerType.IBKR:
        effective_broker = BrokerType.IBKR_FLEX

    # --- Read file with size guard ---
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

    # --- Apply statement_timeout guard (task 5.4) ---
    # Configurable via FRESH_START_TIMEOUT env var (default: 60 s).
    # SET LOCAL is transaction-scoped and resets automatically on commit/rollback.
    timeout_seconds = settings.fresh_start_timeout
    await service.set_statement_timeout(timeout_seconds)

    try:
        result = await service.fresh_start_import(
            content=content,
            filename=filename,
            broker=effective_broker,
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

    return ResponseEnvelope[FreshStartResult](data=result)


@router.patch(
    "/broker-raw-transactions/{raw_id}/suppress",
    response_model=ResponseEnvelope[BrokerRawTransactionRead],
    status_code=status.HTTP_200_OK,
    summary="Suppress or un-suppress a broker raw transaction",
    description=(
        "Toggle the ``suppressed`` flag on a BrokerRawTransaction. "
        "When ``suppressed=true``, the raw transaction is permanently excluded "
        "from all future imports (including fresh-start). "
        "To un-suppress, set ``suppressed=false``."
    ),
    responses={
        200: {"description": "Suppressed flag updated."},
        401: {"description": "Authentication required."},
        404: {"description": "BrokerRawTransaction not found."},
    },
)
async def suppress_raw_transaction(
    raw_id: str,
    service: Annotated[ImportService, Depends(_get_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    suppressed: Annotated[
        bool,
        Query(
            description=(
                "New value for the suppressed flag. True to suppress, False to restore."
            )
        ),
    ] = True,
) -> ResponseEnvelope[BrokerRawTransactionRead]:
    """Toggle the suppressed flag on a broker raw transaction.

    Args:
        raw_id: The composite ID of the raw transaction.
        service: Injected import service.
        current_user: The authenticated user.
        suppressed: When True, suppress the BRT. When False, un-suppress it.

    Returns:
        The updated BrokerRawTransaction.

    Raises:
        HTTPException: 404 if the raw transaction is not found.
    """
    try:
        await service.suppress_raw_transaction(
            raw_id=raw_id,
            user_id=current_user.id,
            suppressed=suppressed,
        )
    except BrokerRawTransactionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    # Reload and return updated BRT
    raw = await service._raw_repo.get_by_id(raw_id)
    if raw is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"BrokerRawTransaction {raw_id} not found.",
        )

    return ResponseEnvelope(data=BrokerRawTransactionRead.model_validate(raw))


@router.post(
    "/flex",
    response_model=ResponseEnvelope[ImportResult],
    status_code=status.HTTP_200_OK,
    summary="Import trades via IBKR Flex Query API",
    description=(
        "Automatically fetch a Flex Query report from the IBKR Flex Web "
        "Service and import all contained trades. "
        "The server must have ``IBKR_FLEX_TOKEN`` configured. "
        "Duplicate trades (same symbol + timestamp already in the database) "
        "are silently skipped."
    ),
    response_description=(
        "A summary of the import operation wrapped in a response envelope, "
        "including the number of trades created and any warnings."
    ),
    responses={
        200: {"description": "Import completed. Check warnings for skipped entries."},
        400: {"description": "Flex API returned an error."},
        401: {"description": "Authentication required."},
        404: {"description": "Account not found or not owned by the current user."},
        429: {"description": "IBKR Flex API rate limit exceeded."},
        503: {"description": "IBKR_FLEX_TOKEN not configured on this server."},
    },
)
async def flex_import(
    service: Annotated[FlexImportService, Depends(_get_flex_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    body: Annotated[FlexImportRequest, Body()],
) -> ResponseEnvelope[ImportResult]:
    """Fetch an IBKR Flex Query report and import the trades it contains.

    Args:
        service: Injected Flex import service.
        current_user: The authenticated user.
        body: Request payload with ``query_id``, optional ``account_id``,
            and optional ``from_date``.

    Returns:
        A :class:`~app.schemas.common.ResponseEnvelope` wrapping an
        :class:`~app.schemas.imports.ImportResult`.

    Raises:
        HTTPException: 400 if the Flex API returns an error.
        HTTPException: 404 if the account is not found or not owned by
            the current user.
        HTTPException: 429 if the IBKR rate limit is hit.
        HTTPException: 503 if the Flex token is not configured.
    """
    try:
        result = await service.import_flex(
            query_id=body.query_id,
            user_id=current_user.id,
            account_id=body.account_id,
            from_date=body.from_date,
            overwrite_manually_edited=body.overwrite_manually_edited,
        )
    except AccountNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except RateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"IBKR Flex API rate limit exceeded. "
                f"Retry after {exc.wait_seconds} seconds."
            ),
            headers={"Retry-After": str(exc.wait_seconds)},
        ) from exc
    except FlexAPIError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return ResponseEnvelope[ImportResult](data=result)
