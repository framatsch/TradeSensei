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

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import ConfigurationError
from app.utils.schwab_client import SchwabClient


def _mock_response(json_data: object) -> MagicMock:
    """Build a mock httpx response that returns *json_data* from .json().

    Args:
        json_data: The data to return from the mocked ``json()`` call.

    Returns:
        A :class:`MagicMock` that looks like an ``httpx.Response``.
    """
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value=json_data)
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
# get_orders
# ---------------------------------------------------------------------------


class TestGetOrders:
    """Tests for :meth:`SchwabClient.get_orders`."""

    async def test_raises_when_no_client_id(self, client: SchwabClient) -> None:
        """Should raise :class:`ConfigurationError` if client_id is absent."""
        with patch("app.utils.schwab_client.settings") as mock_settings:
            mock_settings.schwab_client_id = None
            with pytest.raises(ConfigurationError):
                await client.get_orders("tok", "2024-01-01", "2024-01-31")

    async def test_returns_orders_list(self, client: SchwabClient) -> None:
        """Should return a list of order dicts from the API."""
        orders = [{"orderId": "123", "status": "FILLED"}]
        mock_resp = _mock_response(orders)

        with (
            patch("app.utils.schwab_client.settings") as mock_settings,
            patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_resp)),
        ):
            mock_settings.schwab_client_id = "cid"
            result = await client.get_orders("tok", "2024-01-01", "2024-01-31")

        assert len(result) == 1
        assert result[0]["orderId"] == "123"
