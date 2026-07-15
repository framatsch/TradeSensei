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

"""Unit tests for SchwabClient — all HTTP calls mocked via httpx transport.

Tests verify correct URL construction, parameter passing, error handling,
and ConfigurationError when credentials are missing.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import ConfigurationError
from app.utils.schwab_client import SchwabClient


def _mock_response(
    json_data: object,
    *,
    headers: dict[str, str] | None = None,
) -> MagicMock:
    """Build a mock httpx response that returns *json_data* from .json().

    Args:
        json_data: The data to return from the mocked ``json()`` call.

    Returns:
        A :class:`MagicMock` that looks like an ``httpx.Response``.
    """
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value=json_data)
    resp.headers = headers or {}
    return resp


@pytest.fixture()
def client() -> SchwabClient:
    """Return a :class:`SchwabClient` instance."""
    return SchwabClient()


# ---------------------------------------------------------------------------
# _require_client_id
# ---------------------------------------------------------------------------


class TestRequireClientId:
    """Tests for :meth:`SchwabClient._require_client_id`."""

    def test_raises_when_no_client_id(self, client: SchwabClient) -> None:
        """Should raise :class:`ConfigurationError` when client_id is None."""
        with patch("app.utils.schwab_client.settings") as mock_settings:
            mock_settings.schwab_client_id = None
            with pytest.raises(ConfigurationError, match="SCHWAB_CLIENT_ID"):
                client._require_client_id()

    def test_returns_client_id_when_set(self, client: SchwabClient) -> None:
        """Should return the client_id string when configured."""
        with patch("app.utils.schwab_client.settings") as mock_settings:
            mock_settings.schwab_client_id = "test_id"
            result = client._require_client_id()
            assert result == "test_id"


# ---------------------------------------------------------------------------
# get_authorization_url
# ---------------------------------------------------------------------------


class TestGetAuthorizationUrl:
    """Tests for :meth:`SchwabClient.get_authorization_url`."""

    def test_returns_url_with_expected_params(self, client: SchwabClient) -> None:
        """Should include all required PKCE and OAuth params."""
        with patch("app.utils.schwab_client.settings") as mock_settings:
            mock_settings.schwab_client_id = "my_client"
            mock_settings.schwab_redirect_uri = "http://localhost/callback"
            url = client.get_authorization_url("state123", "challenge_abc")

        assert "response_type=code" in url
        assert "client_id=my_client" in url
        assert "state=state123" in url
        assert "code_challenge=challenge_abc" in url
        assert "code_challenge_method=S256" in url

    def test_raises_when_no_client_id(self, client: SchwabClient) -> None:
        """Should raise :class:`ConfigurationError` when client_id is absent."""
        with patch("app.utils.schwab_client.settings") as mock_settings:
            mock_settings.schwab_client_id = None
            with pytest.raises(ConfigurationError):
                client.get_authorization_url("s", "c")


# ---------------------------------------------------------------------------
# exchange_code
# ---------------------------------------------------------------------------


class TestExchangeCode:
    """Tests for :meth:`SchwabClient.exchange_code`."""

    async def test_raises_when_no_client_secret(self, client: SchwabClient) -> None:
        """Should raise :class:`ConfigurationError` if client_secret is absent."""
        with patch("app.utils.schwab_client.settings") as mock_settings:
            mock_settings.schwab_client_id = "cid"
            mock_settings.schwab_client_secret = None
            with pytest.raises(ConfigurationError, match="SCHWAB_CLIENT_SECRET"):
                await client.exchange_code("code", "verifier")

    async def test_raises_when_no_client_id(self, client: SchwabClient) -> None:
        """Should raise :class:`ConfigurationError` if client_id is absent."""
        with patch("app.utils.schwab_client.settings") as mock_settings:
            mock_settings.schwab_client_id = None
            with pytest.raises(ConfigurationError, match="SCHWAB_CLIENT_ID"):
                await client.exchange_code("code", "verifier")

    async def test_returns_token_response(self, client: SchwabClient) -> None:
        """Should return parsed JSON from the token endpoint."""
        mock_resp = _mock_response(
            {"access_token": "tok", "refresh_token": "ref", "expires_in": 1800}
        )

        with (
            patch("app.utils.schwab_client.settings") as mock_settings,
            patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_resp)),
        ):
            mock_settings.schwab_client_id = "cid"
            mock_settings.schwab_client_secret = "csec"
            mock_settings.schwab_redirect_uri = "http://cb"
            result = await client.exchange_code("mycode", "myverifier")

        assert result["access_token"] == "tok"


# ---------------------------------------------------------------------------
# refresh_access_token
# ---------------------------------------------------------------------------


class TestRefreshAccessToken:
    """Tests for :meth:`SchwabClient.refresh_access_token`."""

    async def test_raises_when_no_client_id(self, client: SchwabClient) -> None:
        """Should raise :class:`ConfigurationError` if client_id is absent."""
        with patch("app.utils.schwab_client.settings") as mock_settings:
            mock_settings.schwab_client_id = None
            with pytest.raises(ConfigurationError):
                await client.refresh_access_token("reftok")

    async def test_raises_when_no_client_secret(self, client: SchwabClient) -> None:
        """Should raise :class:`ConfigurationError` if client_secret is absent."""
        with patch("app.utils.schwab_client.settings") as mock_settings:
            mock_settings.schwab_client_id = "cid"
            mock_settings.schwab_client_secret = None
            with pytest.raises(ConfigurationError):
                await client.refresh_access_token("reftok")

    async def test_returns_token_response(self, client: SchwabClient) -> None:
        """Should return parsed JSON from the token refresh endpoint."""
        mock_resp = _mock_response({"access_token": "newtok", "expires_in": 1800})

        with (
            patch("app.utils.schwab_client.settings") as mock_settings,
            patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_resp)),
        ):
            mock_settings.schwab_client_id = "cid"
            mock_settings.schwab_client_secret = "csec"
            result = await client.refresh_access_token("myref")

        assert result["access_token"] == "newtok"


# ---------------------------------------------------------------------------
# get_account_numbers
# ---------------------------------------------------------------------------


class TestGetAccountNumbers:
    """Tests for :meth:`SchwabClient.get_account_numbers`."""

    async def test_raises_when_no_client_id(self, client: SchwabClient) -> None:
        """Should raise :class:`ConfigurationError` if client_id is absent."""
        with patch("app.utils.schwab_client.settings") as mock_settings:
            mock_settings.schwab_client_id = None
            with pytest.raises(ConfigurationError):
                await client.get_account_numbers("tok")

    async def test_returns_account_number_hash_pairs(self, client: SchwabClient) -> None:
        """Should return normalized accountNumber/hashValue dicts."""
        payload = [
            {"accountNumber": "45302130", "hashValue": "hash-1"},
            {"accountNumber": "", "hashValue": "hash-2"},
        ]
        mock_resp = _mock_response(payload)

        with (
            patch("app.utils.schwab_client.settings") as mock_settings,
            patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_resp)),
        ):
            mock_settings.schwab_client_id = "cid"
            result = await client.get_account_numbers("tok")

        assert result == [{"accountNumber": "45302130", "hashValue": "hash-1"}]


# ---------------------------------------------------------------------------
# get_transactions
# ---------------------------------------------------------------------------


class TestGetTransactions:
    """Tests for :meth:`SchwabClient.get_transactions`."""

    async def test_raises_when_no_client_id(self, client: SchwabClient) -> None:
        """Should raise :class:`ConfigurationError` if client_id is absent."""
        with patch("app.utils.schwab_client.settings") as mock_settings:
            mock_settings.schwab_client_id = None
            with pytest.raises(ConfigurationError):
                await client.get_transactions(
                    "tok",
                    "hash-1",
                    datetime(2026, 1, 1, tzinfo=UTC),
                    datetime(2026, 1, 2, tzinfo=UTC),
                )

    async def test_merges_single_page_transactions(self, client: SchwabClient) -> None:
        """Should return one-page transaction payload unchanged."""
        page = [{"activityId": "1"}, {"activityId": "2"}]
        mock_resp = _mock_response(page)

        with (
            patch("app.utils.schwab_client.settings") as mock_settings,
            patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_resp)),
        ):
            mock_settings.schwab_client_id = "cid"
            result = await client.get_transactions(
                "tok",
                "hash-1",
                datetime(2026, 1, 1, tzinfo=UTC),
                datetime(2026, 1, 2, tzinfo=UTC),
            )

        assert [item["activityId"] for item in result] == ["1", "2"]

    async def test_merges_multipage_transactions_from_link_header(self, client: SchwabClient) -> None:
        """Should follow rel=next links and concatenate all pages."""
        page1 = _mock_response(
            [{"activityId": "1"}],
            headers={"Link": '<https://api.schwabapi.com/trader/v1/accounts/hash-1/transactions?page=2>; rel="next"'},
        )
        page2 = _mock_response([{"activityId": "2"}])

        with (
            patch("app.utils.schwab_client.settings") as mock_settings,
            patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=[page1, page2])),
        ):
            mock_settings.schwab_client_id = "cid"
            result = await client.get_transactions(
                "tok",
                "hash-1",
                datetime(2026, 1, 1, tzinfo=UTC),
                datetime(2026, 1, 2, tzinfo=UTC),
            )

        assert [item["activityId"] for item in result] == ["1", "2"]

    async def test_merges_multipage_transactions_from_next_page_token(self, client: SchwabClient) -> None:
        """Should follow body nextPageToken and concatenate all pages."""
        page1 = _mock_response({"nextPageToken": "abc", "items": "ignored"})
        page1.json = MagicMock(return_value={"nextPageToken": "abc"})
        page2 = _mock_response([{"activityId": "2"}])

        with (
            patch("app.utils.schwab_client.settings") as mock_settings,
            patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=[page1, page2])) as mock_get,
        ):
            mock_settings.schwab_client_id = "cid"
            result = await client.get_transactions(
                "tok",
                "hash-1",
                datetime(2026, 1, 1, tzinfo=UTC),
                datetime(2026, 1, 2, tzinfo=UTC),
            )

        assert [item["activityId"] for item in result] == ["2"]
        second_params = mock_get.await_args_list[1].kwargs["params"]
        assert second_params["nextPageToken"] == "abc"
