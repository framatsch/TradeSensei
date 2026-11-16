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

"""Route handlers for the broker file import endpoint.

Accepts multipart file uploads and delegates to
:class:`~app.services.import_service.ImportService` for parsing and
persisting trades.  Also exposes an IBKR Flex Query automatic import
endpoint backed by :class:`~app.services.flex_import_service.FlexImportService`.
"""

import json
import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, File, HTTPException, Path, Query, UploadFile, status
from fastapi import Form as FastAPIForm
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import IMPORT_BYTES_PER_MB, IMPORT_MAX_FILE_SIZE_MB
from app.core.dependencies import require_portfolio_owner
from app.core.deps import get_current_user, get_session_with_rls
from app.core.exceptions import (
    AccountNotFoundError,
    BrokerRawTransactionNotFoundError,
    FlexAPIError,
    GenericFormatValidationError,
    ImportAccountMismatchError,
    ImportNotAllowedError,
    ImportParseError,
    RateLimitError,
    UnsupportedBrokerError,
)
from app.models.account import AccountType
from app.models.user import User
from app.repositories.account_repository import AccountRepository
from app.schemas.broker_raw_transaction import BrokerRawTransactionRead
from app.schemas.common import ResponseEnvelope
from app.schemas.generic_import import ImportPreviewResult
from app.schemas.imports import FlexImportRequest, FreshStartResult, ImportResult
from app.services.brokers.contracts import BrokerType
from app.services.flex_import_service import FlexImportService, is_transient_send_request_error
from app.services.import_account_service import ImportAccountService
from app.services.import_preview_service import ImportPreviewService
from app.services.import_service import ImportService

router = APIRouter(
    prefix="/portfolios/{portfolio_id}/imports",
    tags=["imports"],
    dependencies=[Depends(require_portfolio_owner)],
)

# 1 MB in bytes.
_BYTES_PER_MB: int = IMPORT_BYTES_PER_MB


_FILE_VALIDATION_RESPONSE = {
    "description": (
        "Invalid request fields, account/file type mismatch, or generic format validation failure. "
        "Generic issues use a detail array of {row, field, code, message}, capped at 200; "
        "row is a zero-based JSON index, a one-based CSV data row, or null for document/account errors. "
        "Messages never echo submitted monetary values."
    ),
    "content": {
        "application/json": {
            "schema": {
                "anyOf": [
                    {"$ref": "#/components/schemas/HTTPValidationError"},
                    {"type": "object", "properties": {"detail": {"type": "string"}}},
                    {
                        "type": "object",
                        "properties": {"detail": {"type": "array", "items": {"$ref": "#/components/schemas/GenericValidationIssue"}}},
                    },
                ]
            },
            "examples": {
                "invalid_timestamp": {
                    "summary": "Generic JSON execution without a UTC offset",
                    "value": {"detail": [{"row": 0, "field": "executed_at", "code": "timezone_aware", "message": "Invalid field value"}]},
                },
                "wrong_account_type": {
                    "summary": "Account does not support this file import",
                    "value": {"detail": "Preview is available only for generic file imports"},
                },
            },
        }
    },
}


def _get_preview_service(session: Annotated[AsyncSession, Depends(get_session_with_rls)]) -> ImportPreviewService:
    """Inject the read-only preview service."""
    return ImportPreviewService(session)


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


def _get_flex_service() -> FlexImportService:
    """FastAPI dependency that constructs a :class:`FlexImportService`.

    ``FlexImportService`` is a pure HTTP client with no database
    dependency, so this factory takes no injected session.

    Returns:
        A :class:`FlexImportService` bound to the configured Flex token.

    Raises:
        HTTPException: 503 if ``IBKR_FLEX_TOKEN`` is not configured.
    """
    token = settings.ibkr_flex_token
    if not token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=("IBKR Flex import is not configured on this server. Set the IBKR_FLEX_TOKEN environment variable to enable it."),
        )
    return FlexImportService(flex_token=token)


async def _validate_account_import(
    account_id: uuid.UUID,
    portfolio_id: uuid.UUID,
    user_id: uuid.UUID,
    extension: str,
    session: AsyncSession,
) -> BrokerType:
    """Verify the account supports file import and the file extension matches.

    Thin HTTP-layer wrapper around
    :meth:`~app.services.import_account_service.ImportAccountService.validate_file`,
    which owns the single implementation shared with the preview endpoint.

    Args:
        account_id: UUID of the target account.
        portfolio_id: UUID of the portfolio owning the account.
        user_id: UUID of the authenticated user.
        extension: Lowercase file extension (without leading dot).
        session: Database session for the account lookup.

    Returns:
        The :class:`BrokerType` key of the adapter to import with.

    Raises:
        ImportNotAllowedError: If the account type has no file import, or the
            file extension does not match the expected format for the account
            type.
        AccountNotFoundError: If the account does not exist or is not owned by
            the user.
    """
    return await ImportAccountService(session).validate_file(account_id, portfolio_id, user_id, extension)


@router.post(
    "/upload",
    response_model=ResponseEnvelope[ImportResult],
    status_code=status.HTTP_200_OK,
    summary="Upload a broker export file and import trades",
    description=(
        "Parse a broker export file and bulk-create the contained trades for "
        "the specified account. The accepted file format is determined by the "
        "account type: IBKR accounts accept XML (Flex Query), Schwab accounts "
        "accept JSON; GENERIC accounts accept Trade Sensei Execution Format v1 "
        "JSON or CSV, not broker-native files. Manual accounts do not support file import. "
        "Generic validation is all-or-nothing. The first successful generic import locks "
        "the account to external_id or fingerprint identity; switching strategies is rejected "
        "until all account trades are cleared. Re-imported raw identities are deduplicated, "
        "suppression and manual-edit protections are preserved, and conflicting generic split "
        "ratios are never overwritten. Preview generic files at the sibling /preview endpoint "
        "before confirming an upload. Format schema and CSV template are available under "
        "/api/v1/imports/formats/generic. CSV contains executions only; splits require JSON. "
        f"Maximum file size: {IMPORT_MAX_FILE_SIZE_MB} MB."
    ),
    response_description=("A summary of the import operation wrapped in a response envelope, including the number of trades created and any parse warnings."),
    responses={
        200: {"description": "Import completed. Check warnings for skipped rows."},
        400: {"description": "File format not supported or parse error."},
        401: {"description": "Authentication required."},
        404: {"description": "Portfolio or account not found, not owned by the current user, or account outside the portfolio."},
        413: {"description": "File exceeds the maximum allowed size."},
        422: _FILE_VALIDATION_RESPONSE,
    },
)
async def upload_import(
    portfolio_id: Annotated[
        uuid.UUID, Path(description="UUID of the owned portfolio containing the target account.", examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"])
    ],
    service: Annotated[ImportService, Depends(_get_service)],
    session: Annotated[AsyncSession, Depends(get_session_with_rls)],
    current_user: Annotated[User, Depends(get_current_user)],
    file: Annotated[
        UploadFile,
        File(
            description=(
                "Broker export selected by filename extension: IBKR .xml, Schwab .json, or GENERIC .json/.csv. Generic JSON carries format/version and "
                "executions; CSV requires a UTF-8 comma-delimited header with flattened option columns."
            ),
            examples=["executions.json", "executions.csv"],
        ),
    ],
    account_id: Annotated[
        uuid.UUID,
        FastAPIForm(
            description="UUID of the owned account in this portfolio; its type selects the import format.", examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"]
        ),
    ],
    overwrite_manually_edited: Annotated[
        bool,
        FastAPIForm(
            description=(
                "When true, trades that have been manually edited are no longer "
                "protected and will be overwritten by the incoming import data. "
                "Defaults to false."
            ),
            examples=[False, True],
        ),
    ] = False,
) -> ResponseEnvelope[ImportResult]:
    """Upload a broker export file and import the trades it contains.

    The broker parser is determined automatically from the account type:
    IBKR accounts use the XML (Flex Query) parser, Schwab accounts use the
    JSON parser. GENERIC accounts accept the versioned JSON/CSV execution
    format; manual accounts are rejected with HTTP 422. Generic validation
    completes before writes, and account identity strategy is locked on import.

    Args:
        service: Injected import service.
        portfolio_id: UUID of the owned portfolio containing the account.
        session: Database session used for the account type lookup.
        current_user: The authenticated user.
        file: The uploaded file.
        account_id: UUID of the target broker account.
        overwrite_manually_edited: When ``True``, manually-edited trades
            are overwritten instead of skipped.

    Returns:
        A :class:`~app.schemas.common.ResponseEnvelope` wrapping an
        :class:`~app.schemas.imports.ImportResult` with counts and
        any non-fatal warnings.

    Raises:
        HTTPException: 400 if the file cannot be parsed.
        HTTPException: 401 if authentication is missing or invalid.
        HTTPException: 404 if the account is not found or not owned by
            the current user.
        HTTPException: 413 if the uploaded file exceeds the size limit.
        HTTPException: 422 if the file type does not match the account type,
            the account is manual, generic rows fail validation, the recorded
            ID strategy conflicts, or Schwab account matching fails.
    """
    filename = file.filename or "upload"
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    # --- Validate account type and file extension --------------------------
    try:
        broker = await _validate_account_import(
            account_id=account_id,
            portfolio_id=portfolio_id,
            user_id=current_user.id,
            extension=extension,
            session=session,
        )
    except AccountNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ImportNotAllowedError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    # --- Read file content with size guard ---------------------------------
    max_bytes = IMPORT_MAX_FILE_SIZE_MB * _BYTES_PER_MB
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=(f"File exceeds the maximum allowed size of {IMPORT_MAX_FILE_SIZE_MB} MB."),
        )

    # --- Delegate to service -----------------------------------------------
    try:
        result = await service.import_trades(
            content=content,
            filename=filename,
            broker=broker,
            portfolio_id=portfolio_id,
            account_id=account_id,
            user_id=current_user.id,
            overwrite_manually_edited=overwrite_manually_edited,
        )
    except AccountNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except GenericFormatValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=exc.errors) from exc
    except ImportNotAllowedError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except (ImportParseError, UnsupportedBrokerError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ImportAccountMismatchError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logging.getLogger(__name__).exception("Unhandled exception during import_trades")
        if isinstance(exc, ValidationError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Validation error during import parsing: {exc}",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process import file. An unexpected error occurred: {exc}",
        ) from exc

    return ResponseEnvelope[ImportResult](data=result)


@router.post(
    "/preview",
    response_model=ResponseEnvelope[ImportPreviewResult],
    status_code=status.HTTP_200_OK,
    summary="Preview a generic execution file without writing changes",
    description=(
        "Validate a Trade Sensei Execution Format v1 .json or .csv upload for a GENERIC "
        "account and report execution identity novelty, recorded/detected ID strategies, "
        "suppressed records and split conflicts. This is a read-only raw-level preview, "
        "not an aggregation or prediction of trade counts; no executions, trades, splits "
        "or account properties are written. A strategy conflict is reported in a successful "
        "HTTP 200 response; a later upload will reject it with HTTP 422. Invalid files return "
        "HTTP 422 with row-level issues in detail, not an ImportPreviewResult envelope. "
        "Existing split ratios are preserved. Confirm by sending the same multipart form "
        "to /upload. In fingerprint mode, differing counts of identical fills in overlapping "
        "exports can affect ordinal deduplication; inspect already_imported before confirming. "
        f"Maximum file size: {IMPORT_MAX_FILE_SIZE_MB} MB."
    ),
    response_description="Read-only execution-level counts and compatibility information wrapped in data.",
    responses={
        200: {
            "description": "Preview completed; check strategy_conflict and warnings before upload.",
            "content": {
                "application/json": {
                    "example": {
                        "data": {
                            "detected_strategy": "external_id",
                            "recorded_strategy": "external_id",
                            "strategy_conflict": False,
                            "total": 10,
                            "new": 7,
                            "already_imported": 3,
                            "suppressed": 1,
                            "new_splits": 0,
                            "conflicting_splits": 1,
                            "warnings": ["split_conflict: existing split ratio preserved"],
                            "errors": [],
                        }
                    }
                }
            },
        },
        401: {"description": "Authentication required."},
        404: {"description": "Portfolio or account not found, not owned by the current user, or account outside the portfolio."},
        413: {"description": "File exceeds the maximum allowed size."},
        422: _FILE_VALIDATION_RESPONSE,
    },
)
async def preview_import(
    portfolio_id: Annotated[
        uuid.UUID, Path(description="UUID of the owned portfolio containing the target GENERIC account.", examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"])
    ],
    service: Annotated[ImportPreviewService, Depends(_get_preview_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    file: Annotated[
        UploadFile,
        File(
            description=(
                "Trade Sensei Execution Format v1 file with a .json or .csv filename; CSV contains executions only, while JSON may also declare splits."
            ),
            examples=["executions.json", "executions.csv"],
        ),
    ],
    account_id: Annotated[
        uuid.UUID, FastAPIForm(description="UUID of the owned GENERIC account in this portfolio.", examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"])
    ],
    overwrite_manually_edited: Annotated[
        bool,
        FastAPIForm(description="Accepted for upload parity but ignored by preview; counts remain raw-level and no protections are changed.", examples=[False]),
    ] = False,
) -> ResponseEnvelope[ImportPreviewResult]:
    """Validate a generic file and preview identity novelty without writes.

    Args:
        portfolio_id: UUID of the owned portfolio containing the account.
        service: Injected read-only import preview service.
        current_user: The authenticated user.
        file: Versioned generic JSON or header-based CSV execution file.
        account_id: UUID of the target GENERIC account.
        overwrite_manually_edited: Ignored; accepted for upload form parity.

    Returns:
        An envelope containing raw-level counts, strategies and split warnings.
        Strategy conflicts are reported without failing the preview request.

    Raises:
        HTTPException: 401 if authentication is missing or invalid.
        HTTPException: 404 if the portfolio/account is unavailable to the user.
        HTTPException: 413 if the file exceeds the import size limit.
        HTTPException: 422 for unsupported account/file types, invalid request
            fields, or generic validation issues returned in a detail array.
    """
    del overwrite_manually_edited
    max_bytes = IMPORT_MAX_FILE_SIZE_MB * IMPORT_BYTES_PER_MB
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="File exceeds the import size limit")
    try:
        result = await service.preview(content, file.filename or "upload", portfolio_id, account_id, current_user.id)
    except AccountNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ImportNotAllowedError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except GenericFormatValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=exc.errors) from exc
    return ResponseEnvelope(data=result)


@router.post(
    "/{account_id}/fresh-start",
    response_model=ResponseEnvelope[FreshStartResult],
    status_code=status.HTTP_200_OK,
    summary="Fresh-start: reset account and re-import from scratch",
    description=(
        "Destructive operation — deletes ALL ``LogicalExecution``, ``Trade`` and "
        "``BrokerRawTransaction`` rows for the specified account, then processes the "
        "uploaded file. "
        "The entire operation runs in a single DB transaction — any error rolls "
        "back all changes. "
        "The accepted file format is determined by the account type: IBKR accepts "
        "XML (Flex Query), Schwab accepts JSON, GENERIC accepts Trade Sensei Execution "
        "Format v1 JSON or CSV. Because the account is emptied, a recorded generic ID "
        "strategy is released as well, so the uploaded file may switch between "
        "external_id and fingerprint identity."
    ),
    responses={
        200: {"description": "Fresh-start completed. Check import_result for details."},
        400: {"description": "File format not supported or parse error."},
        401: {"description": "Authentication required."},
        404: {"description": "Account not found or not owned by the current user."},
        413: {"description": "File exceeds the maximum allowed size."},
        422: _FILE_VALIDATION_RESPONSE,
    },
)
async def fresh_start_import(
    portfolio_id: uuid.UUID,
    account_id: uuid.UUID,
    service: Annotated[ImportService, Depends(_get_service)],
    session: Annotated[AsyncSession, Depends(get_session_with_rls)],
    current_user: Annotated[User, Depends(get_current_user)],
    file: UploadFile,
    acknowledged: Annotated[
        bool,
        FastAPIForm(description=("Must be true to confirm that all trades and executions for this account will be deleted before re-importing.")),
    ] = False,
) -> ResponseEnvelope[FreshStartResult]:
    """Reset an account and re-import all trades from a broker file.

    The broker parser is determined automatically from the account type.
    Emptying the account also releases a recorded generic ID strategy, so the
    uploaded file may use either identity strategy.

    Args:
        portfolio_id: UUID of the portfolio owning the account.
        account_id: UUID of the account to reset.
        service: Injected import service.
        session: Database session used for the account type lookup.
        current_user: The authenticated user.
        file: The uploaded broker export file.
        acknowledged: Must be True to confirm the destructive action.

    Returns:
        A fresh-start result with delete counts and the import result.

    Raises:
        HTTPException: 400 if ``acknowledged`` is False or the file cannot be parsed.
        HTTPException: 404 if the account is not found.
        HTTPException: 413 if the file is too large.
        HTTPException: 422 if the file type does not match the account type,
            or generic rows fail validation.
    """
    if not acknowledged:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=("Please set acknowledged=true to confirm that all trades and executions for this account will be deleted before re-importing."),
        )

    filename = file.filename or "upload"
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    # --- Validate account type and file extension --------------------------
    try:
        broker = await _validate_account_import(
            account_id=account_id,
            portfolio_id=portfolio_id,
            user_id=current_user.id,
            extension=extension,
            session=session,
        )
    except AccountNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ImportNotAllowedError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    # --- Read file with size guard ---
    max_bytes = IMPORT_MAX_FILE_SIZE_MB * _BYTES_PER_MB
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=(f"File exceeds the maximum allowed size of {IMPORT_MAX_FILE_SIZE_MB} MB."),
        )

    # --- Apply statement_timeout guard ---
    timeout_seconds = settings.fresh_start_timeout
    await service.set_statement_timeout(timeout_seconds)

    try:
        result = await service.fresh_start_import(
            content=content,
            filename=filename,
            broker=broker,
            portfolio_id=portfolio_id,
            account_id=account_id,
            user_id=current_user.id,
        )
    except AccountNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except GenericFormatValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=exc.errors) from exc
    except (ImportNotAllowedError, ImportAccountMismatchError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except (ImportParseError, UnsupportedBrokerError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logging.getLogger(__name__).exception("Unhandled exception during fresh_start_import")
        if isinstance(exc, ValidationError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Validation error during import parsing: {exc}",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process import file. An unexpected error occurred: {exc}",
        ) from exc

    return ResponseEnvelope[FreshStartResult](data=result)


@router.post(
    "/schwab-json",
    response_model=ResponseEnvelope[ImportResult],
    status_code=status.HTTP_200_OK,
    summary="Import Schwab transactions from JSON body",
    description=(
        "Import Schwab transactions from a wrapped JSON object body "
        "({fetchedAt, dateRange, accounts:[...]}). The target account must be "
        "a SCHWAB account. Returns 422 for Schwab account mismatch/ambiguity."
    ),
    responses={
        200: {"description": "Import completed."},
        400: {"description": "Import payload is invalid or cannot be parsed."},
        401: {"description": "Authentication required."},
        404: {"description": "Account not found or not owned by the current user."},
        422: {"description": "Account type is not SCHWAB or Schwab account mismatch/ambiguity."},
    },
)
async def import_schwab_json(
    portfolio_id: uuid.UUID,
    service: Annotated[ImportService, Depends(_get_service)],
    session: Annotated[AsyncSession, Depends(get_session_with_rls)],
    current_user: Annotated[User, Depends(get_current_user)],
    account_id: Annotated[
        uuid.UUID,
        Query(description="UUID of the Schwab account to import into."),
    ],
    body: Annotated[dict[str, object], Body()],
) -> ResponseEnvelope[ImportResult]:
    """Import Schwab transaction JSON directly from request body."""
    account = await AccountRepository(session).get_by_id(
        account_id,
        current_user.id,
        portfolio_id,
    )
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {account_id} not found for user {current_user.id}.",
        )
    if account.type != AccountType.SCHWAB:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Account type must be SCHWAB for this endpoint",
        )

    try:
        content = json.dumps(body).encode("utf-8")
        result = await service.import_trades(
            content=content,
            filename="schwab_transactions.json",
            broker=BrokerType.SCHWAB,
            portfolio_id=portfolio_id,
            account_id=account_id,
            user_id=current_user.id,
        )
    except (ImportParseError, UnsupportedBrokerError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ImportAccountMismatchError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        import logging

        logging.getLogger(__name__).exception("Unhandled exception during import_trades")
        from pydantic import ValidationError

        if isinstance(exc, ValidationError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Validation error during import parsing: {exc}",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process import file. An unexpected error occurred: {exc}",
        ) from exc

    return ResponseEnvelope[ImportResult](data=result)


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
    portfolio_id: uuid.UUID,
    raw_id: str,
    service: Annotated[ImportService, Depends(_get_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    suppressed: Annotated[
        bool,
        Query(description=("New value for the suppressed flag. True to suppress, False to restore.")),
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
            portfolio_id=portfolio_id,
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
        "Service and import it through the same unified import pipeline used "
        "by file uploads. The server must have ``IBKR_FLEX_TOKEN`` configured."
    ),
    response_description=("A summary of the import operation wrapped in a response envelope, including the number of trades created and any warnings."),
    responses={
        200: {"description": "Import completed. Check warnings for skipped entries."},
        400: {"description": "Flex API returned a non-transient error, the fetched XML could not be parsed, or an unexpected error occurred."},
        401: {"description": "Authentication required."},
        404: {"description": "Account not found or not owned by the current user."},
        422: {"description": "Import account mismatch reported by the shared import pipeline."},
        429: {"description": "IBKR Flex API rate limit exceeded."},
        503: {"description": "IBKR_FLEX_TOKEN not configured on this server, or the Flex API is temporarily unavailable — retry later, not immediately."},
    },
)
async def flex_import(
    portfolio_id: uuid.UUID,
    flex_service: Annotated[FlexImportService, Depends(_get_flex_service)],
    import_service: Annotated[ImportService, Depends(_get_service)],
    session: Annotated[AsyncSession, Depends(get_session_with_rls)],
    current_user: Annotated[User, Depends(get_current_user)],
    body: Annotated[FlexImportRequest, Body()],
    account_id: Annotated[
        uuid.UUID | None,
        Query(description="Optional UUID of the account to import trades into."),
    ] = None,
) -> ResponseEnvelope[ImportResult]:
    """Fetch an IBKR Flex Query report and import the trades it contains.

    Args:
        flex_service: Injected Flex API client service.
        import_service: Injected unified import service.
        session: Database session used for optional account ownership lookup.
        current_user: The authenticated user.
        account_id: Optional account UUID supplied as a query parameter.
            When provided, it takes precedence over ``body.account_id``;
            the body field remains supported for callers that only send
            it in the JSON payload.
        body: Request payload with ``query_id``, optional ``account_id``,
            and optional ``from_date``.

    Returns:
        A :class:`~app.schemas.common.ResponseEnvelope` wrapping an
        :class:`~app.schemas.imports.ImportResult`.

    Raises:
        HTTPException: 400 if the Flex API returns a non-transient error,
            the fetched XML cannot be parsed, or another unexpected error
            occurs while importing.
        HTTPException: 404 if the account is not found or not owned by
            the current user.
        HTTPException: 422 if the shared import pipeline reports an
            account mismatch.
        HTTPException: 429 if the IBKR rate limit is hit.
        HTTPException: 503 if the Flex token is not configured, or the
            Flex API reports a transient generation delay. IBKR's own
            guidance is to wait minutes, not seconds, before retrying —
            this endpoint does not retry automatically.
    """
    resolved_account_id = account_id if account_id is not None else body.account_id

    try:
        if resolved_account_id is not None:
            account = await AccountRepository(session).get_by_id(
                resolved_account_id,
                current_user.id,
                portfolio_id,
            )
            if account is None:
                raise AccountNotFoundError(f"Account {resolved_account_id} not found for user {current_user.id}.")

        xml_content = await flex_service.fetch_flex_report(
            query_id=body.query_id,
            from_date=body.from_date,
        )
        result = await import_service.import_trades(
            content=xml_content,
            filename=f"flex_query_{body.query_id}.xml",
            broker=BrokerType.IBKR,
            portfolio_id=portfolio_id,
            account_id=resolved_account_id,
            user_id=current_user.id,
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
            detail=(f"IBKR Flex API rate limit exceeded. Retry after {exc.wait_seconds} seconds."),
            headers={"Retry-After": str(exc.wait_seconds)},
        ) from exc
    except FlexAPIError as exc:
        if is_transient_send_request_error(str(exc)):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(f"IBKR Flex API temporarily unavailable: {exc}"),
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except (ImportParseError, UnsupportedBrokerError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ImportAccountMismatchError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        import logging

        logging.getLogger(__name__).exception("Unhandled exception during flex import")
        from pydantic import ValidationError

        if isinstance(exc, ValidationError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Validation error during import parsing: {exc}",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process Flex import. An unexpected error occurred: {exc}",
        ) from exc

    return ResponseEnvelope[ImportResult](data=result)
