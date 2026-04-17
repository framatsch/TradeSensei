"""Utility for fetching EUR/USD daily exchange rates from the ECB.

Uses the ECB Statistical Data Warehouse SDMX-REST API to retrieve the
official EZB reference rate.  This rate is the legally recognised rate for
German income tax (§20 EStG) purposes.

API endpoint:
    https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A
    ?detail=dataonly&startPeriod=YYYY-MM-DD&endPeriod=YYYY-MM-DD

The response is an SDMX-JSON document.  We parse the ``dataSets[0].series``
structure to extract the rate value.  When no rate exists for a date
(weekend / public holiday), the API returns HTTP 200 with an empty
observations dict — the parser returns ``None`` in that case and the
caller retries with an earlier date.
"""

import datetime as dt
import logging
from decimal import Decimal, InvalidOperation

import httpx

from app.core.constants import (
    FX_ECB_FALLBACK_DAYS,
    FX_ECB_TIMEOUT_SECONDS,
)

logger = logging.getLogger(__name__)

_ECB_BASE_URL: str = (
    "https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A"
)


async def fetch_ecb_rate(date: dt.date) -> Decimal | None:
    """Fetch the official EUR/USD daily rate from the ECB.

    Requests the EZB reference rate for *date*.  If no rate is available
    (weekend / public holiday), automatically retries up to
    :data:`~app.core.constants.FX_ECB_FALLBACK_DAYS` days earlier.

    Args:
        date: The calendar date for which the rate is needed.

    Returns:
        The EUR/USD rate as a :class:`~decimal.Decimal`
        (i.e. ``1 USD = <rate> EUR``), or ``None`` if the API is
        unreachable or returns no data within the fallback window.
    """
    for delta in range(FX_ECB_FALLBACK_DAYS + 1):
        lookup_date = date - dt.timedelta(days=delta)
        rate = await _fetch_single_date(lookup_date)
        if rate is not None:
            if delta > 0:
                logger.info(
                    "No ECB rate for %s — using rate from %s"
                    " (%d day(s) earlier).",
                    date,
                    lookup_date,
                    delta,
                )
            return rate

    logger.warning(
        "No ECB EUR/USD rate found for %s or the %d preceding days.",
        date,
        FX_ECB_FALLBACK_DAYS,
    )
    return None


async def _fetch_single_date(date: dt.date) -> Decimal | None:
    """Fetch the ECB rate for exactly one calendar date.

    Args:
        date: The calendar date to query.

    Returns:
        The rate as :class:`~decimal.Decimal`, or ``None`` if the API
        returns an error, times out, or returns no observations.
    """
    date_str = date.isoformat()
    params = {
        "detail": "dataonly",
        "startPeriod": date_str,
        "endPeriod": date_str,
    }
    try:
        async with httpx.AsyncClient(timeout=FX_ECB_TIMEOUT_SECONDS) as client:
            response = await client.get(
                _ECB_BASE_URL,
                params=params,
                headers={"Accept": "application/json"},
            )
        response.raise_for_status()
        return _parse_sdmx_response(response.json(), date_str)
    except httpx.TimeoutException:
        logger.warning(
            "ECB API timed out after %.1fs for date %s.",
            FX_ECB_TIMEOUT_SECONDS,
            date,
        )
        return None
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "ECB API returned HTTP %d for date %s: %s",
            exc.response.status_code,
            date,
            exc.response.text[:200],
        )
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning("ECB API unexpected error for date %s: %s", date, exc)
        return None


def _parse_sdmx_response(data: object, date_str: str) -> Decimal | None:
    """Extract the EUR/USD rate from an SDMX-JSON response payload.

    The ECB SDMX-JSON structure is::

        {
          "dataSets": [
            {
              "series": {
                "0:0:0:0:0": {
                  "observations": {
                    "0": [<rate_value>]
                  }
                }
              }
            }
          ]
        }

    When no rate exists for the requested date (weekend / public holiday),
    the API returns HTTP 200 with an empty ``observations`` dict — this
    function returns ``None`` in that case.

    Args:
        data: Parsed JSON response body (may be any type).
        date_str: ISO date string — used only for log messages.

    Returns:
        The rate as :class:`~decimal.Decimal`, or ``None`` if parsing fails
        or no observation is present.
    """
    try:
        if not isinstance(data, dict):
            logger.warning("ECB response for %s is not a dict.", date_str)
            return None

        datasets = data.get("dataSets")
        if not datasets or not isinstance(datasets, list):
            return None

        series = datasets[0].get("series", {})
        if not series:
            return None

        # The first (and only) series key.
        first_series = next(iter(series.values()), None)
        if first_series is None:
            return None

        observations = first_series.get("observations", {})
        if not observations:
            return None

        # Observation key "0" is the first (and only) time point.
        obs_values = observations.get("0")
        if not obs_values or not isinstance(obs_values, list):
            return None

        raw_value = obs_values[0]
        if raw_value is None:
            return None

        return Decimal(str(raw_value))

    except (InvalidOperation, KeyError, IndexError, TypeError) as exc:
        logger.warning(
            "Failed to parse ECB SDMX response for %s: %s", date_str, exc
        )
        return None
