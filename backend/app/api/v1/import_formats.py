"""Authenticated downloads for the broker-neutral execution format."""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, status
from starlette.responses import Response, StreamingResponse

from app.core.constants import GENERIC_SCHEMA_PREFIX
from app.core.deps import get_current_user
from app.schemas.generic_import import GenericFormatSchema
from app.services.generic_format_service import GenericFormatService

router = APIRouter(prefix=GENERIC_SCHEMA_PREFIX, tags=["imports"], dependencies=[Depends(get_current_user)])


def _get_service() -> GenericFormatService:
    """Inject the stateless format publication service."""
    return GenericFormatService()


# Raw streaming download: JSON Schema consumers require top-level schema keys,
# not a response envelope. The declared response shape is the JSON Schema DTO.
@router.get(
    "",
    response_model=None,
    response_class=StreamingResponse,
    responses={
        status.HTTP_200_OK: {"model": GenericFormatSchema, "description": "JSON Schema of the Trade Sensei Execution Format v1 document."},
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required."},
    },
    summary="Download generic execution JSON Schema",
)
async def generic_schema(service: Annotated[GenericFormatService, Depends(_get_service)]) -> StreamingResponse:
    """Stream the complete machine-readable JSON Schema without an envelope."""
    content = json.dumps(service.schema().model_dump(by_alias=True)).encode("utf-8")
    return StreamingResponse(iter([content]), media_type="application/schema+json")


# Raw binary CSV download is deliberately not wrapped in ResponseEnvelope.
@router.get(
    "/template.csv",
    response_model=None,
    response_class=Response,
    summary="Download generic execution CSV template",
    responses={
        status.HTTP_200_OK: {"content": {"text/csv": {}}, "description": "CSV header row followed by two example executions."},
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required."},
    },
)
async def generic_csv_template(service: Annotated[GenericFormatService, Depends(_get_service)]) -> Response:
    """Download a model-derived header and two example executions."""
    return Response(service.template(), media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="tradesensei-executions-v1.csv"'})
