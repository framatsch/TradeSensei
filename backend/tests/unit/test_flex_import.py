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

import uuid
import xml.etree.ElementTree as ET
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AccountNotFoundError, FlexAPIError, RateLimitError
from app.services.flex_import_service import (
    FlexImportService,
    _is_transient_send_request_error,
    _parse_wait_time,
    _text,
)

pytestmark = pytest.mark.asyncio

_USER_ID = uuid.uuid4()
_PORTFOLIO_ID = uuid.uuid4()
_ACCOUNT_ID = uuid.uuid4()


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
    assert _is_transient_send_request_error("Statement could not be generated at this time") is True
    assert _is_transient_send_request_error("Please try again shortly") is True


async def test_is_transient_returns_false_for_unknown_error():
    assert _is_transient_send_request_error("Rate limit exceeded") is False


# ---------------------------------------------------------------------------
# FlexImportService helpers
# ---------------------------------------------------------------------------


def _make_service(
    account_repo=None,
    portfolio_repo=None,
    trade_repo=None,
    parser=None,
):
    svc = FlexImportService.__new__(FlexImportService)
    svc._session = AsyncMock()
    svc._token = "test-token"
    svc._timeout = 30
    svc._account_repo = account_repo or AsyncMock()
    svc._portfolio_repo = portfolio_repo or AsyncMock()
    svc._trade_repo = trade_repo or AsyncMock()
    svc._parser = parser or MagicMock()
    return svc


def _make_mock_account():
    a = MagicMock()
    a.id = _ACCOUNT_ID
    return a


def _make_mock_portfolio(base_currency: str = "USD"):
    p = MagicMock()
    p.id = _PORTFOLIO_ID
    p.base_currency = base_currency
    return p


def _make_parsed_trade(symbol: str = "AAPL", currency: str = "USD"):
    t = MagicMock()
    t.symbol = symbol
    t.currency = currency
    t.opened_at = datetime(2024, 1, 15, 9, 30)
    t.broker_conid = "12345"
    t.account_id = None
    t.user_id = None
    t.model_copy = MagicMock(return_value=t)
    return t


# ---------------------------------------------------------------------------
# import_flex — account validation
# ---------------------------------------------------------------------------


async def test_import_flex_raises_when_account_not_found():
    svc = _make_service()
    svc._account_repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(AccountNotFoundError):
        await svc.import_flex(
            query_id="123",
            user_id=_USER_ID,
            portfolio_id=_PORTFOLIO_ID,
            account_id=_ACCOUNT_ID,
        )


async def test_import_flex_skips_account_check_when_no_account_id():
    """When account_id is None, no account lookup should happen."""
    svc = _make_service()
    svc._account_repo.get_by_id = AsyncMock()

    trade = _make_parsed_trade()
    svc._parser.parse = MagicMock(return_value=([trade], []))
    svc._parser.warnings = []
    svc._portfolio_repo.get_by_id = AsyncMock(return_value=_make_mock_portfolio())
    svc._trade_repo.list_manually_edited_keys = AsyncMock(return_value=set())
    svc._trade_repo.find_duplicate = AsyncMock(return_value=True)

    with patch.object(svc, "_fetch_flex_xml", return_value="<xml/>"):
        result = await svc.import_flex(
            query_id="123",
            user_id=_USER_ID,
            portfolio_id=_PORTFOLIO_ID,
            account_id=None,
        )

    svc._account_repo.get_by_id.assert_not_called()
    assert result.trades_skipped == 1


async def test_import_flex_skips_duplicate_trades():
    svc = _make_service()

    trade = _make_parsed_trade()
    svc._parser.parse = MagicMock(return_value=([trade], []))
    svc._parser.warnings = []
    svc._portfolio_repo.get_by_id = AsyncMock(return_value=_make_mock_portfolio())
    svc._trade_repo.list_manually_edited_keys = AsyncMock(return_value=set())
    svc._trade_repo.find_duplicate = AsyncMock(return_value=True)

    with patch.object(svc, "_fetch_flex_xml", return_value="<xml/>"):
        result = await svc.import_flex(
            query_id="123",
            user_id=_USER_ID,
            portfolio_id=_PORTFOLIO_ID,
        )

    assert result.trades_skipped == 1
    assert result.trades_created == 0


async def test_import_flex_creates_new_trade():
    """Create a new trade from a parsed Flex trade when no duplicate exists.

    Regression guard: a successful create must be reported only via
    ``activity_log``, never surfaced as a false warning.
    """
    svc = _make_service()

    trade = _make_parsed_trade()
    svc._parser.parse = MagicMock(return_value=([trade], []))
    svc._parser.warnings = []
    svc._portfolio_repo.get_by_id = AsyncMock(return_value=_make_mock_portfolio())
    svc._trade_repo.list_manually_edited_keys = AsyncMock(return_value=set())
    svc._trade_repo.find_duplicate = AsyncMock(return_value=False)
    svc._trade_repo.create = AsyncMock()

    with patch.object(svc, "_fetch_flex_xml", return_value="<xml/>"):
        result = await svc.import_flex(
            query_id="123",
            user_id=_USER_ID,
            portfolio_id=_PORTFOLIO_ID,
        )

    assert result.trades_created == 1
    assert result.trades_skipped == 0
    assert result.warnings == []
    assert any("created:" in line for line in result.activity_log)


async def test_import_flex_skips_manually_edited_trades():
    svc = _make_service()

    trade = _make_parsed_trade()
    # The match key is (broker_conid, opened_at) — we put it in manually_edited_keys
    match_key = (trade.broker_conid, trade.opened_at)
    svc._parser.parse = MagicMock(return_value=([trade], []))
    svc._parser.warnings = []
    svc._portfolio_repo.get_by_id = AsyncMock(return_value=_make_mock_portfolio())
    svc._trade_repo.list_manually_edited_keys = AsyncMock(return_value={match_key})
    svc._trade_repo.find_duplicate = AsyncMock(return_value=False)

    with patch.object(svc, "_fetch_flex_xml", return_value="<xml/>"):
        result = await svc.import_flex(
            query_id="123",
            user_id=_USER_ID,
            portfolio_id=_PORTFOLIO_ID,
        )

    assert result.trades_skipped == 1


async def test_import_flex_adds_currency_mismatch_warning():
    svc = _make_service()

    trade = _make_parsed_trade(currency="EUR")  # EUR but portfolio base is USD
    svc._parser.parse = MagicMock(return_value=([trade], []))
    svc._parser.warnings = []
    svc._portfolio_repo.get_by_id = AsyncMock(return_value=_make_mock_portfolio(base_currency="USD"))
    svc._trade_repo.list_manually_edited_keys = AsyncMock(return_value=set())
    svc._trade_repo.find_duplicate = AsyncMock(return_value=True)  # skip creation

    with patch.object(svc, "_fetch_flex_xml", return_value="<xml/>"):
        result = await svc.import_flex(
            query_id="123",
            user_id=_USER_ID,
            portfolio_id=_PORTFOLIO_ID,
        )

    assert any("currency_mismatch" in w for w in result.warnings)


async def test_import_flex_handles_trade_create_exception():
    svc = _make_service()

    trade = _make_parsed_trade()
    svc._parser.parse = MagicMock(return_value=([trade], []))
    svc._parser.warnings = []
    svc._portfolio_repo.get_by_id = AsyncMock(return_value=_make_mock_portfolio())
    svc._trade_repo.list_manually_edited_keys = AsyncMock(return_value=set())
    svc._trade_repo.find_duplicate = AsyncMock(return_value=False)
    svc._trade_repo.create = AsyncMock(side_effect=Exception("DB error"))

    with patch.object(svc, "_fetch_flex_xml", return_value="<xml/>"):
        result = await svc.import_flex(
            query_id="123",
            user_id=_USER_ID,
            portfolio_id=_PORTFOLIO_ID,
        )

    assert result.trades_skipped == 1
    assert any("Failed to persist" in w for w in result.warnings)


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
# _send_request_with_retries
# ---------------------------------------------------------------------------


async def test_send_request_with_retries_propagates_rate_limit_immediately():
    svc = _make_service()

    mock_client = AsyncMock()

    with patch.object(svc, "_send_request_once", side_effect=RateLimitError("rate limited", 900)), pytest.raises(RateLimitError):
        await svc._send_request_with_retries(mock_client, "https://example.com", {})


async def test_send_request_with_retries_retries_transient_error():
    svc = _make_service()
    mock_client = AsyncMock()

    call_count = 0

    async def _flaky(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise FlexAPIError("statement could not be generated at this time")
        return "REF123"

    with patch.object(svc, "_send_request_once", side_effect=_flaky), patch("app.services.flex_import_service.asyncio.sleep", new=AsyncMock()):
        result = await svc._send_request_with_retries(mock_client, "https://example.com", {})

    assert result == "REF123"
    assert call_count == 2
