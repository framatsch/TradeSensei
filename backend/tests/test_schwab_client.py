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

"""Unit tests for SchwabClient with explicit OAuth credential parameters."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.utils.schwab_client import SchwabClient


def _mock_response(json_data: object, *, headers: dict[str, str] | None = None) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value=json_data)
    resp.headers = headers or {}
    return resp


@pytest.fixture()
def client() -> SchwabClient:
    return SchwabClient()


class TestGetAuthorizationUrl:
    def test_returns_url_with_expected_params(self, client: SchwabClient) -> None:
        url = client.get_authorization_url(
            state="state123",
            code_challenge="challenge_abc",
            client_id="my_client",
            redirect_uri="https://127.0.0.1",
        )
        assert "response_type=code" in url
        assert "client_id=my_client" in url
        assert "redirect_uri=https%3A%2F%2F127.0.0.1" in url
        assert "state=state123" in url
        assert "code_challenge=challenge_abc" in url
        assert "code_challenge_method=S256" in url


class TestExchangeCode:
    async def test_returns_token_response(self, client: SchwabClient) -> None:
        mock_resp = _mock_response({"access_token": "tok", "refresh_token": "ref", "expires_in": 1800})
        with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_resp)):
            result = await client.exchange_code(
                code="mycode",
                code_verifier="myverifier",
                client_id="cid",
                client_secret="csec",
                redirect_uri="https://127.0.0.1",
            )
        assert result["access_token"] == "tok"


class TestRefreshAccessToken:
    async def test_returns_token_response(self, client: SchwabClient) -> None:
        mock_resp = _mock_response({"access_token": "newtok", "expires_in": 1800})
        with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_resp)):
            result = await client.refresh_access_token(
                refresh_token="myref",
                client_id="cid",
                client_secret="csec",
                redirect_uri="https://127.0.0.1",
            )
        assert result["access_token"] == "newtok"


class TestGetAccountNumbers:
    async def test_returns_account_number_hash_pairs(self, client: SchwabClient) -> None:
        payload = [{"accountNumber": "45302130", "hashValue": "hash-1"}, {"accountNumber": "", "hashValue": "hash-2"}]
        mock_resp = _mock_response(payload)
        with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_resp)):
            result = await client.get_account_numbers("tok")
        assert result == [{"accountNumber": "45302130", "hashValue": "hash-1"}]


class TestGetTransactions:
    async def test_merges_multipage_transactions_from_link_header(self, client: SchwabClient) -> None:
        page1 = _mock_response(
            [{"activityId": "1"}],
            headers={"Link": '<https://api.schwabapi.com/trader/v1/accounts/hash-1/transactions?page=2>; rel="next"'},
        )
        page2 = _mock_response([{"activityId": "2"}])
        with patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=[page1, page2])):
            result = await client.get_transactions(
                "tok",
                "hash-1",
                datetime(2026, 1, 1, tzinfo=UTC),
                datetime(2026, 1, 2, tzinfo=UTC),
            )
        assert [item["activityId"] for item in result] == ["1", "2"]
