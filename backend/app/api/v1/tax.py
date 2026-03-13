"""Route handlers for the ``/api/v1/tax`` resource.

Provides two endpoints for German Anlage KAP tax reporting:

- ``GET /tax/annual-summary?year=YYYY`` — JSON summary grouped by §20 EStG
  categories (equities vs. derivatives).
- ``GET /tax/annual-summary/csv?year=YYYY`` — same data as a downloadable
  CSV file suitable for manual entry into the Anlage KAP form.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.common import ResponseEnvelope
from app.schemas.tax import TaxAnnualSummary
from app.services.tax_service import TaxService

router = APIRouter(prefix="/tax", tags=["tax"])


def _get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TaxService:
    """FastAPI dependency that constructs a :class:`TaxService`.

    Args:
        session: Injected async database session.

    Returns:
        A :class:`TaxService` bound to the current session.
    """
    return TaxService(session)


@router.get(
    "/annual-summary",
    response_model=ResponseEnvelope[TaxAnnualSummary],
    summary="Get Annual Tax Summary (§20 EStG)",
    description=(
        "Return the annual tax summary for the authenticated user, grouped "
        "by German §20 EStG categories for Anlage KAP reporting.\n\n"
        "**Categories:**\n"
        "- **equities**: §20 Abs. 2 Nr. 1 EStG — realised gains/losses from "
        "``AssetClass.EQUITY`` trades.\n"
        "- **derivatives**: §20 Abs. 2 Nr. 3 EStG — realised gains/losses from "
        "all other asset classes (options, futures, forex, crypto).\n\n"
        "Only *closed* trades (where ``pnl IS NOT NULL``) are considered. "
        "The ``pnl_eur`` field is populated during broker import via the "
        "official Bundesbank daily EUR/USD rate.\n\n"
        "When no trades with a known ``pnl_eur`` exist for the requested year, "
        "all monetary values are returned as ``0`` (HTTP 200 — not 404).\n\n"
        "**Authentication:** a valid Bearer token is required."
    ),
    response_description=(
        "Annual tax summary with equities and derivatives blocks plus "
        "``total_net_eur``, wrapped in a ResponseEnvelope."
    ),
    responses={
        200: {"description": "Tax summary successfully computed and returned."},
        401: {
            "description": (
                "Not authenticated. The Bearer token is missing, expired, or invalid."
            )
        },
        422: {
            "description": (
                "Query parameter validation error. ``year`` must be a valid integer."
            )
        },
    },
)
async def get_annual_summary(
    service: Annotated[TaxService, Depends(_get_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    year: Annotated[
        int,
        Query(
            ge=1900,
            le=2200,
            description=(
                "Calendar year for which to compute the tax summary "
                "(e.g. ``2025``). Must be between 1900 and 2200."
            ),
            examples=[2025],
        ),
    ],
) -> ResponseEnvelope[TaxAnnualSummary]:
    """Compute and return the annual tax summary for the current user.

    Fetches closed trades for the requested year, groups them by §20 EStG
    category, and returns the aggregated EUR P&L totals.

    Args:
        service: Injected tax service that orchestrates data access and
            computation.
        current_user: The currently authenticated user, resolved from the
            Bearer token by the ``get_current_user`` dependency.
        year: Calendar year to summarise.

    Returns:
        A :class:`~app.schemas.common.ResponseEnvelope` whose ``data`` field
        contains a fully populated :class:`~app.schemas.tax.TaxAnnualSummary`.

    Raises:
        HTTPException: 401 if the Bearer token is missing, expired, or
            otherwise invalid.
    """
    summary = await service.get_annual_summary(
        year=year,
        user_id=current_user.id,
    )
    return ResponseEnvelope[TaxAnnualSummary](data=summary)


@router.get(
    "/annual-summary/csv",
    summary="Download Annual Tax CSV (Anlage KAP)",
    description=(
        "Download the annual tax data as a CSV file for manual entry into "
        "the German Anlage KAP tax form.\n\n"
        "**Columns:** Symbol, Asset-Klasse, Kategorie, Eröffnungsdatum, "
        "Schließungsdatum, P&L (USD), EUR/USD-Kurs, P&L (EUR).\n\n"
        "The file uses UTF-8 with BOM encoding for compatibility with "
        "Microsoft Excel on Windows.\n\n"
        "All closed trades for the year are included, even those where "
        "``pnl_eur`` could not be determined (EUR/USD rate unavailable at "
        "import time) — those rows will have empty EUR columns.\n\n"
        "**Authentication:** a valid Bearer token is required."
    ),
    responses={
        200: {
            "description": "CSV file successfully generated.",
            "content": {"text/csv": {}},
        },
        401: {
            "description": (
                "Not authenticated. The Bearer token is missing, expired, or invalid."
            )
        },
        422: {
            "description": (
                "Query parameter validation error. ``year`` must be a valid integer."
            )
        },
    },
)
async def get_annual_summary_csv(
    service: Annotated[TaxService, Depends(_get_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    year: Annotated[
        int,
        Query(
            ge=1900,
            le=2200,
            description=(
                "Calendar year for which to generate the CSV export "
                "(e.g. ``2025``). Must be between 1900 and 2200."
            ),
            examples=[2025],
        ),
    ],
) -> StreamingResponse:
    """Generate and stream the annual tax CSV for the current user.

    Fetches all closed trades for the requested year, computes the implied
    EUR/USD rate per trade where possible, and streams the result as a
    ``text/csv`` attachment.

    Args:
        service: Injected tax service that orchestrates data access and
            CSV generation.
        current_user: The currently authenticated user, resolved from the
            Bearer token by the ``get_current_user`` dependency.
        year: Calendar year to export.

    Returns:
        A :class:`~fastapi.responses.StreamingResponse` with
        ``Content-Type: text/csv`` and a ``Content-Disposition: attachment``
        header that suggests the filename ``steuer_<year>.csv``.

    Raises:
        HTTPException: 401 if the Bearer token is missing, expired, or
            otherwise invalid.
    """
    csv_content = await service.get_annual_csv(
        year=year,
        user_id=current_user.id,
    )
    filename = f"steuer_{year}.csv"
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
