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

"""Unit tests for FlexImportService and module-level helpers."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import FlexAPIError, RateLimitError
from app.services.flex_import_service import (
    FlexImportService,
    _parse_wait_time,
    _text,
    is_transient_send_request_error,
)

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


async def test_text_returns_none_for_none_element():
    assert _text(None) is None


async def test_text_returns_none_for_element_with_no_text():
    elem = ET.Element("Test")
    assert _text(elem) is None


async def test_text_strips_whitespace():
    elem = ET.Element("Test")
    elem.text = "  hello  "
    assert _text(elem) == "hello"


async def test_text_returns_none_for_empty_string():
    elem = ET.Element("Test")
    elem.text = "   "
    assert _text(elem) is None


async def test_parse_wait_time_extracts_minutes():
    msg = "Please try again in 15 minutes"
    assert _parse_wait_time(msg) == 15 * 60


async def test_parse_wait_time_defaults_when_no_match():
    assert _parse_wait_time("Some other error") == 900


async def test_parse_wait_time_case_insensitive():
    msg = "Please try again in 5 Minutes"
    assert _parse_wait_time(msg) == 300


async def test_is_transient_detects_known_messages():
    assert is_transient_send_request_error("Statement could not be generated at this time") is True
    assert is_transient_send_request_error("Please try again shortly") is True


async def test_is_transient_returns_false_for_unknown_error():
    assert is_transient_send_request_error("Rate limit exceeded") is False


# ---------------------------------------------------------------------------
# FlexImportService helpers
# ---------------------------------------------------------------------------


def _make_service() -> FlexImportService:
    svc = FlexImportService.__new__(FlexImportService)
    svc._token = "test-token"
    svc._timeout = 30
    return svc


async def test_fetch_flex_report_returns_xml_bytes():
    svc = _make_service()

    with patch.object(svc, "_fetch_flex_xml", new=AsyncMock(return_value="<xml/>")):
        payload = await svc.fetch_flex_report(query_id="123")

    assert payload == b"<xml/>"


# ---------------------------------------------------------------------------
# _send_request_once
# ---------------------------------------------------------------------------


async def test_send_request_once_raises_on_http_error():
    svc = _make_service()

    import httpx

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=httpx.RequestError("connection error"))

    with pytest.raises(FlexAPIError, match="HTTP error"):
        await svc._send_request_once(mock_client, "https://example.com", {})


async def test_send_request_once_raises_on_invalid_xml():
    svc = _make_service()

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.text = "not valid xml"

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    with pytest.raises(FlexAPIError, match="Invalid XML"):
        await svc._send_request_once(mock_client, "https://example.com", {})


async def test_send_request_once_raises_rate_limit_on_1019():
    svc = _make_service()

    xml = """<FlexStatementResponse>
    <Status>Fail</Status>
    <ErrorCode>1019</ErrorCode>
    <ErrorMessage>Please try again in 15 minutes</ErrorMessage>
    </FlexStatementResponse>"""

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.text = xml

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    with pytest.raises(RateLimitError) as exc_info:
        await svc._send_request_once(mock_client, "https://example.com", {})

    assert exc_info.value.wait_seconds == 900  # 15 * 60


async def test_send_request_once_raises_flex_api_error_on_failure():
    svc = _make_service()

    xml = """<FlexStatementResponse>
    <Status>Fail</Status>
    <ErrorCode>9999</ErrorCode>
    <ErrorMessage>Some error</ErrorMessage>
    </FlexStatementResponse>"""

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.text = xml

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    with pytest.raises(FlexAPIError, match="Some error"):
        await svc._send_request_once(mock_client, "https://example.com", {})


async def test_send_request_once_raises_when_no_reference_code():
    svc = _make_service()

    xml = """<FlexStatementResponse>
    <Status>Success</Status>
    <ReferenceCode></ReferenceCode>
    </FlexStatementResponse>"""

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.text = xml

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    with pytest.raises(FlexAPIError, match="missing ReferenceCode"):
        await svc._send_request_once(mock_client, "https://example.com", {})


async def test_send_request_once_returns_reference_code_on_success():
    svc = _make_service()

    xml = """<FlexStatementResponse>
    <Status>Success</Status>
    <ReferenceCode>REF123</ReferenceCode>
    </FlexStatementResponse>"""

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.text = xml

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    result = await svc._send_request_once(mock_client, "https://example.com", {})
    assert result == "REF123"


# ---------------------------------------------------------------------------
# _poll_report
# ---------------------------------------------------------------------------


async def test_poll_report_returns_xml_when_ready():
    svc = _make_service()

    xml = """<FlexQueryResponse><FlexStatements><Trade/></FlexStatements></FlexQueryResponse>"""

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.text = xml

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch("app.services.flex_import_service.asyncio.sleep", new=AsyncMock()):
        result = await svc._poll_report(mock_client, "REF123")

    assert "FlexQueryResponse" in result


async def test_poll_report_raises_on_non_1018_error():
    svc = _make_service()

    xml = """<FlexStatementResponse>
    <Status>Fail</Status>
    <ErrorCode>9999</ErrorCode>
    <ErrorMessage>Fatal error</ErrorMessage>
    </FlexStatementResponse>"""

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.text = xml

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch("app.services.flex_import_service.asyncio.sleep", new=AsyncMock()), pytest.raises(FlexAPIError, match="Fatal error"):
        await svc._poll_report(mock_client, "REF123")


async def test_poll_report_raises_timeout_after_max_attempts():

    svc = _make_service()

    # Return 1018 (still generating) every time
    xml = """<FlexStatementResponse>
    <Status>Warn</Status>
    <ErrorCode>1018</ErrorCode>
    <ErrorMessage>Still generating</ErrorMessage>
    </FlexStatementResponse>"""

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.text = xml

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch("app.services.flex_import_service.asyncio.sleep", new=AsyncMock()), pytest.raises(FlexAPIError, match="not ready after"):
        await svc._poll_report(mock_client, "REF123")


# ---------------------------------------------------------------------------
# _send_request — no in-process retry
# ---------------------------------------------------------------------------


async def test_send_request_propagates_rate_limit_immediately():
    svc = _make_service()

    mock_client = AsyncMock()

    with patch.object(svc, "_send_request_once", side_effect=RateLimitError("rate limited", 900)), pytest.raises(RateLimitError):
        await svc._send_request(mock_client, "query-1", None)


async def test_send_request_does_not_retry_transient_error():
    """A transient generation error must surface on the first attempt.

    Regression guard: retrying in-process within seconds was observed to
    itself trip IBKR's "Too many failed attempts" account-level lockout.
    """
    svc = _make_service()
    mock_client = AsyncMock()

    call_count = 0

    async def _flaky(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        raise FlexAPIError("statement could not be generated at this time")

    with (
        patch.object(svc, "_send_request_once", side_effect=_flaky),
        patch("app.services.flex_import_service.asyncio.sleep", new=AsyncMock()) as mock_sleep,
        pytest.raises(FlexAPIError, match="statement could not be generated"),
    ):
        await svc._send_request(mock_client, "query-1", None)

    assert call_count == 1
    mock_sleep.assert_not_awaited()
