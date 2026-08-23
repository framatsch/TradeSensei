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

"""IBKR Flex Web Service client.

This service only executes the Flex request-and-poll protocol and returns the
raw Flex Query XML payload. Parsing, aggregation, deduplication, and
persistence are handled by :class:`~app.services.import_service.ImportService`.
"""

import asyncio
import logging
import re
import xml.etree.ElementTree as ET

import httpx

from app.core.constants import (
    FLEX_API_VERSION,
    FLEX_BASE_URL,
    FLEX_POLL_INTERVAL_SECONDS,
    FLEX_POLL_MAX_ATTEMPTS,
)
from app.core.exceptions import FlexAPIError, RateLimitError

logger = logging.getLogger(__name__)

_FLEX_TRANSIENT_SEND_REQUEST_MESSAGES = (
    "statement could not be generated at this time",
    "please try again shortly",
)
"""Substrings of IBKR ``ErrorMessage`` text that indicate the Flex report
generation needs more time. IBKR's own recommended cooldown between
consecutive Flex Query generations for the same query is on the order of
minutes, not seconds, so these are surfaced immediately rather than
retried in-process. A tight local retry loop was observed to itself
trigger IBKR's stricter "Too many failed attempts" account-level lockout
by presenting as a rapid-fire burst against the SendRequest endpoint."""


class FlexImportService:
    """Service for fetching IBKR Flex Query XML.

    Wraps the two-step Flex API call (send request -> poll for result) and
    returns report XML bytes unchanged. This is a pure HTTP client with no
    database dependency — it does not parse, aggregate, or persist trade
    data; see :class:`~app.services.import_service.ImportService` for that.

    Args:
        flex_token: IBKR Flex Web Service token.  Typically read from
            application settings by the caller.
        http_timeout: Timeout in seconds for individual HTTP requests
            to the Flex API.
    """

    def __init__(
        self,
        flex_token: str,
        http_timeout: int = 60,
    ) -> None:
        """Initialise the service.

        Args:
            flex_token: IBKR Flex Web Service token.
            http_timeout: Per-request timeout in seconds.
        """
        self._token = flex_token
        self._timeout = http_timeout

    # ─── Public method ────────────────────────────────────────────────────────

    async def fetch_flex_report(
        self,
        *,
        query_id: str,
        from_date: str | None = None,
    ) -> bytes:
        """Fetch a Flex Query report and return raw XML bytes.

        Args:
            query_id: IBKR Flex Query ID (configured in Account Management).
            from_date: Optional start date in ``YYYYMMDD`` format passed to
                the Flex API to restrict the report period.

        Returns:
            Raw XML bytes of the completed Flex Query report.
        """
        xml_string = await self._fetch_flex_xml(query_id=query_id, from_date=from_date)
        return xml_string.encode("utf-8")

    # ─── Flex API helpers ─────────────────────────────────────────────────────

    async def _fetch_flex_xml(self, query_id: str, from_date: str | None) -> str:
        """Execute the two-step Flex API request-and-poll workflow.

        Args:
            query_id: IBKR Flex Query ID.
            from_date: Optional start date in ``YYYYMMDD`` format.

        Returns:
            Raw XML string of the Flex Query report.

        Raises:
            FlexAPIError: On any Flex API error.
            RateLimitError: When IBKR rate-limits the request (error 1019).
        """
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            reference_code = await self._send_request(client, query_id, from_date)
            return await self._poll_report(client, reference_code)

    async def _send_request(
        self,
        client: httpx.AsyncClient,
        query_id: str,
        from_date: str | None,
    ) -> str:
        """Send the initial Flex Query generation request.

        Makes exactly one attempt. IBKR's own guidance for a "please try
        again shortly" response is to wait on the order of minutes before
        the next Flex Query generation for the same query, so this method
        deliberately does not retry in-process — a short, tight retry loop
        was observed to itself trip IBKR's stricter "Too many failed
        attempts" account-level lockout. Callers that want to retry after a
        transient failure should do so with a substantial delay (minutes),
        driven by the caller/user rather than automatically here.

        Args:
            client: Shared :class:`httpx.AsyncClient` instance.
            query_id: IBKR Flex Query ID.
            from_date: Optional start date filter (``YYYYMMDD``).

        Returns:
            The ``ReferenceCode`` to use for polling.

        Raises:
            FlexAPIError: On HTTP or API-level errors. Use
                :func:`is_transient_send_request_error` on the message to
                distinguish a temporary generation delay from a genuine
                configuration problem.
            RateLimitError: When IBKR responds with error code ``1019``.
        """
        base_params: dict[str, str] = {
            "t": self._token,
            "q": query_id,
            "v": FLEX_API_VERSION,
        }
        url = f"{FLEX_BASE_URL}/FlexStatementService.SendRequest"
        logger.info("Requesting Flex Query %s generation…", query_id)

        params = dict(base_params)
        if from_date:
            params["period"] = from_date
        return await self._send_request_once(client=client, url=url, params=params)

    async def _send_request_once(
        self,
        client: httpx.AsyncClient,
        url: str,
        params: dict[str, str],
    ) -> str:
        """Send one Flex SendRequest call and return the polling reference code."""

        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise FlexAPIError(f"HTTP error sending Flex request: {exc}") from exc

        try:
            root = ET.fromstring(response.text)
        except ET.ParseError as exc:
            raise FlexAPIError(f"Invalid XML in Flex SendRequest response: {exc}") from exc

        status_elem = root.find("Status")
        if status_elem is None or status_elem.text != "Success":
            error_code = _text(root.find("ErrorCode"))
            error_msg = _text(root.find("ErrorMessage")) or "Unknown error"
            if error_code and "1019" in error_code:
                wait_seconds = _parse_wait_time(error_msg)
                raise RateLimitError(error_msg, wait_seconds)
            raise FlexAPIError(f"Flex SendRequest failed: {error_msg}")

        ref_elem = root.find("ReferenceCode")
        ref_code = _text(ref_elem)
        if not ref_code:
            raise FlexAPIError("Invalid Flex SendRequest response: missing ReferenceCode.")

        logger.info("Flex Query generation requested; reference code: %s", ref_code)
        return ref_code

    async def _poll_report(
        self,
        client: httpx.AsyncClient,
        reference_code: str,
    ) -> str:
        """Poll the Flex API until the report is ready.

        Args:
            client: Shared :class:`httpx.AsyncClient` instance.
            reference_code: Code received from :meth:`_send_request`.

        Returns:
            XML string of the completed report.

        Raises:
            FlexAPIError: If the report fails or polling times out.
        """
        url = f"{FLEX_BASE_URL}/FlexStatementService.GetStatement"
        params = {
            "t": self._token,
            "q": reference_code,
            "v": FLEX_API_VERSION,
        }

        for attempt in range(1, FLEX_POLL_MAX_ATTEMPTS + 1):
            await asyncio.sleep(FLEX_POLL_INTERVAL_SECONDS)
            logger.debug(
                "Polling for Flex report (attempt %d/%d)…",
                attempt,
                FLEX_POLL_MAX_ATTEMPTS,
            )

            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise FlexAPIError(f"HTTP error polling Flex report: {exc}") from exc

            try:
                root = ET.fromstring(response.text)
            except ET.ParseError as exc:
                raise FlexAPIError(f"Invalid XML in Flex GetStatement response: {exc}") from exc

            # Report is ready when the root element is FlexQueryResponse.
            if root.tag == "FlexQueryResponse":
                logger.info("Flex report ready after %d attempt(s).", attempt)
                return ET.tostring(root, encoding="unicode")

            # Otherwise it's a FlexStatementResponse with a status code.
            status = _text(root.find("Status"))
            code = _text(root.find("ErrorCode"))
            msg = _text(root.find("ErrorMessage")) or "Unknown"

            if status == "Warn" and code and "1018" in code:
                # 1018 = report still being generated, keep polling.
                continue

            raise FlexAPIError(f"Flex GetStatement error (status={status}): {msg}")

        raise FlexAPIError(f"Flex report not ready after {FLEX_POLL_MAX_ATTEMPTS} polling attempts.")


# ─── Module-level helpers ─────────────────────────────────────────────────────


def _text(elem: ET.Element | None) -> str | None:
    """Return the text content of an XML element, or ``None``.

    Args:
        elem: An :class:`~xml.etree.ElementTree.Element` or ``None``.

    Returns:
        The stripped text content, or ``None`` if the element is absent
        or has no text.
    """
    if elem is None:
        return None
    return (elem.text or "").strip() or None


def _parse_wait_time(error_message: str) -> int:
    """Extract the wait duration from an IBKR rate-limit error message.

    IBKR messages typically read: ``"Please try again in X minutes"``.

    Args:
        error_message: The raw IBKR error message string.

    Returns:
        Wait time in seconds.  Defaults to 900 (15 minutes) when the
        duration cannot be extracted.
    """
    match = re.search(r"(\d+)\s+minute", error_message, re.IGNORECASE)
    if match:
        return int(match.group(1)) * 60
    return 900


def is_transient_send_request_error(error_message: str) -> bool:
    """Detect Flex SendRequest error messages that are usually temporary.

    Public — used by callers (``BrokerService``, the ``/imports/flex``
    route handler) to decide whether a ``FlexAPIError`` should be mapped
    to HTTP 503 (temporary, safe to retry after a substantial delay) or
    to a genuine configuration error.
    """
    msg = error_message.lower()
    return any(marker in msg for marker in _FLEX_TRANSIENT_SEND_REQUEST_MESSAGES)
