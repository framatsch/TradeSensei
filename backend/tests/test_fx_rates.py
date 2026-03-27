"""Unit tests for the Bundesbank FX-rate utilities.

All tests are pure unit tests — no database access.
HTTP calls are intercepted with ``pytest-httpx`` / ``unittest.mock``.
"""

import datetime as dt
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.utils.fx_rates import _parse_sdmx_response, fetch_bundesbank_rate

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _sdmx_payload(rate: float) -> dict:
    """Build a minimal valid SDMX-JSON payload with a single observation.

    Args:
        rate: The rate value to embed.

    Returns:
        A dict that matches the expected Bundesbank SDMX-JSON structure.
    """
    return {
        "dataSets": [
            {
                "series": {
                    "0:0:0:0:0": {
                        "observations": {
                            "0": [rate],
                        }
                    }
                }
            }
        ]
    }


# ─── _parse_sdmx_response ─────────────────────────────────────────────────────


class TestParseSdmxResponse:
    """Tests for the pure SDMX parsing helper."""

    def test_parses_valid_payload(self) -> None:
        """Returns a Decimal for a well-formed SDMX payload."""
        payload = _sdmx_payload(0.9123)
        result = _parse_sdmx_response(payload, "2024-03-15")
        assert result == Decimal("0.9123")

    def test_returns_none_for_non_dict(self) -> None:
        """Returns None when the payload is not a dict."""
        assert _parse_sdmx_response("not a dict", "2024-03-15") is None

    def test_returns_none_for_empty_datasets(self) -> None:
        """Returns None when dataSets is empty."""
        assert _parse_sdmx_response({"dataSets": []}, "2024-03-15") is None

    def test_returns_none_for_missing_datasets(self) -> None:
        """Returns None when dataSets key is absent."""
        assert _parse_sdmx_response({}, "2024-03-15") is None

    def test_returns_none_for_empty_series(self) -> None:
        """Returns None when series dict is empty."""
        payload = {"dataSets": [{"series": {}}]}
        assert _parse_sdmx_response(payload, "2024-03-15") is None

    def test_returns_none_for_empty_observations(self) -> None:
        """Returns None when the observations dict is empty."""
        payload = {"dataSets": [{"series": {"0:0:0:0:0": {"observations": {}}}}]}
        assert _parse_sdmx_response(payload, "2024-03-15") is None

    def test_returns_none_when_obs_value_is_none(self) -> None:
        """Returns None when the first observation value is None."""
        payload = {
            "dataSets": [{"series": {"0:0:0:0:0": {"observations": {"0": [None]}}}}]
        }
        assert _parse_sdmx_response(payload, "2024-03-15") is None

    def test_returns_none_for_invalid_decimal(self) -> None:
        """Returns None gracefully when the value cannot be converted to Decimal."""
        payload = {
            "dataSets": [
                {"series": {"0:0:0:0:0": {"observations": {"0": ["not-a-number"]}}}}
            ]
        }
        assert _parse_sdmx_response(payload, "2024-03-15") is None


# ─── fetch_bundesbank_rate ─────────────────────────────────────────────────────


class TestFetchBundesbankRate:
    """Tests for fetch_bundesbank_rate with mocked HTTP calls."""

    @pytest.mark.asyncio
    async def test_returns_rate_for_weekday(self) -> None:
        """Returns Decimal rate when the API responds successfully on first try."""
        date = dt.date(2024, 3, 15)  # Friday
        payload = _sdmx_payload(0.9200)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = payload
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("app.utils.fx_rates.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_bundesbank_rate(date)

        assert result == Decimal("0.92")
        mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_fallback_on_weekend(self) -> None:
        """Returns rate from the previous Friday when Saturday returns 404."""
        saturday = dt.date(2024, 3, 16)  # Saturday
        dt.date(2024, 3, 15)

        def _make_response(date: dt.date) -> MagicMock:
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            if date == saturday:
                resp.status_code = 404
            else:
                resp.status_code = 200
                resp.json.return_value = _sdmx_payload(0.9150)
            return resp

        call_count = 0

        # Use Any to avoid pyright complaints about kwargs parameter types.
        from typing import Any  # noqa: PLC0415

        async def _fake_get(url: str, **kwargs: Any) -> MagicMock:
            nonlocal call_count
            # Determine which date is being requested from startPeriod param.
            params: dict[str, str] = kwargs.get("params", {})
            start: str = params.get("startPeriod", "")
            req_date = dt.date.fromisoformat(start)
            call_count += 1
            return _make_response(req_date)

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = _fake_get

        with patch("app.utils.fx_rates.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_bundesbank_rate(saturday)

        assert result == Decimal("0.915")
        assert call_count == 2  # Saturday (404) + Friday (200)

    @pytest.mark.asyncio
    async def test_returns_none_when_all_fallbacks_fail(self) -> None:
        """Returns None when all fallback dates return 404."""
        date = dt.date(2024, 1, 1)  # New Year's Day

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("app.utils.fx_rates.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_bundesbank_rate(date)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_timeout(self) -> None:
        """Returns None when the API call times out (no exception propagated)."""
        import httpx

        date = dt.date(2024, 3, 15)

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        with patch("app.utils.fx_rates.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_bundesbank_rate(date)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_http_error(self) -> None:
        """Returns None when the API returns a non-404 HTTP error."""
        import httpx

        date = dt.date(2024, 3, 15)

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        def _raise_for_status() -> None:
            raise httpx.HTTPStatusError(
                "500", request=MagicMock(), response=mock_response
            )

        mock_response.raise_for_status = _raise_for_status
        mock_response.json.return_value = {}
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("app.utils.fx_rates.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_bundesbank_rate(date)

        assert result is None
