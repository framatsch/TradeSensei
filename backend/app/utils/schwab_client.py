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

"""HTTP client for the Schwab OAuth 2.0 + REST API.

Provides :class:`SchwabClient` which handles PKCE authorization URL
construction, authorization-code exchange, token refresh, account lookup,
and transaction retrieval. All network calls use ``httpx``.
"""

from __future__ import annotations

import urllib.parse
from datetime import UTC, datetime
from typing import Any

import httpx


class SchwabClient:
    """Thin HTTP client for Schwab's OAuth 2.0 and broker REST API.

    All methods that make network calls are ``async``.  The client raises
    :class:`~app.core.exceptions.ConfigurationError` as soon as any method
    is called when ``SCHWAB_CLIENT_ID`` is not configured.

    Attributes:
        BASE_URL: Root URL for all Schwab API endpoints.
        AUTH_URL: Authorization endpoint for the OAuth 2.0 flow.
        TOKEN_URL: Token endpoint for code exchange and refresh.
    """

    BASE_URL: str = "https://api.schwabapi.com/trader/v1"
    AUTH_URL: str = "https://api.schwabapi.com/v1/oauth/authorize"
    TOKEN_URL: str = "https://api.schwabapi.com/v1/oauth/token"  # noqa: S105

    def get_authorization_url(
        self,
        *,
        state: str,
        code_challenge: str,
        client_id: str,
        redirect_uri: str,
    ) -> str:
        """Build and return the OAuth 2.0 PKCE authorization URL.

        Constructs the Schwab authorization URL with the required PKCE
        parameters so the user can be redirected for consent.

        Args:
            state: A cryptographically random state parameter for CSRF
                protection.
            code_challenge: The SHA-256 PKCE code challenge derived from
                the code verifier.

        Returns:
            A fully-qualified authorization URL string.

        """
        params: dict[str, str] = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": "readonly",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return f"{self.AUTH_URL}?{urllib.parse.urlencode(params)}"

    async def exchange_code(
        self,
        *,
        code: str,
        code_verifier: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
    ) -> dict[str, Any]:
        """Exchange an authorization code for access and refresh tokens.

        Performs a ``POST`` to the Schwab token endpoint with the
        ``authorization_code`` grant type and PKCE ``code_verifier``.

        Args:
            code: The authorization code received from the callback redirect.
            code_verifier: The original PKCE code verifier string generated
                before the authorization request.

        Returns:
            A dictionary containing at minimum ``access_token``,
            ``refresh_token``, and ``expires_in`` keys.

        Raises:
            :class:`httpx.HTTPStatusError`: If the token endpoint returns a non-2xx response.
        """
        import base64

        auth_string = f"{client_id}:{client_secret}"
        b64_auth = base64.b64encode(auth_string.encode("ascii")).decode("ascii")
        headers = {"Authorization": f"Basic {b64_auth}", "Content-Type": "application/x-www-form-urlencoded"}

        payload: dict[str, str] = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(self.TOKEN_URL, data=payload, headers=headers)
            response.raise_for_status()
            result: dict[str, Any] = response.json()
            return result

    async def refresh_access_token(
        self,
        *,
        refresh_token: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
    ) -> dict[str, Any]:
        """Use a refresh token to obtain a new access token.

        Args:
            refresh_token: A valid Schwab OAuth refresh token.

        Returns:
            A dictionary containing at minimum ``access_token`` and
            ``expires_in`` keys.

        Raises:
            :class:`httpx.HTTPStatusError`: If the token endpoint returns a non-2xx response.
        """
        import base64

        auth_string = f"{client_id}:{client_secret}"
        b64_auth = base64.b64encode(auth_string.encode("ascii")).decode("ascii")
        headers = {"Authorization": f"Basic {b64_auth}", "Content-Type": "application/x-www-form-urlencoded"}

        payload: dict[str, str] = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "redirect_uri": redirect_uri,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(self.TOKEN_URL, data=payload, headers=headers)
            response.raise_for_status()
            result: dict[str, Any] = response.json()
            return result

    async def get_account_numbers(self, access_token: str) -> list[dict[str, object]]:
        """Fetch Schwab account-number/hash mappings for the current user."""
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.BASE_URL}/accounts/accountNumbers", headers=headers)
            response.raise_for_status()
            payload = response.json()

        if not isinstance(payload, list):
            return []

        result: list[dict[str, object]] = []
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            account_number = str(entry.get("accountNumber", "")).strip()
            hash_value = str(entry.get("hashValue", "")).strip()
            if not account_number or not hash_value:
                continue
            result.append(
                {
                    "accountNumber": account_number,
                    "hashValue": hash_value,
                }
            )
        return result

    async def get_transactions(
        self,
        access_token: str,
        account_hash: str,
        from_date: datetime,
        to_date: datetime,
    ) -> list[dict[str, Any]]:
        """Fetch all paginated Schwab TRADE transactions for one account hash."""
        headers = {"Authorization": f"Bearer {access_token}"}
        base_params: dict[str, str] = {
            "types": "TRADE",
            "startDate": self._format_transactions_datetime(from_date),
            "endDate": self._format_transactions_datetime(to_date),
        }

        all_transactions: list[dict[str, Any]] = []
        next_url: str | None = f"{self.BASE_URL}/accounts/{account_hash}/transactions"
        next_params: dict[str, str] | None = dict(base_params)
        seen_pages: set[str] = set()

        async with httpx.AsyncClient() as client:
            while next_url:
                page_key = self._page_key(next_url, next_params)
                if page_key in seen_pages:
                    break
                seen_pages.add(page_key)

                response = await client.get(
                    next_url,
                    headers=headers,
                    params=next_params,
                )
                response.raise_for_status()
                payload = response.json()
                if isinstance(payload, list):
                    all_transactions.extend(item for item in payload if isinstance(item, dict))

                link_next = self._extract_next_link(response.headers.get("Link"))
                if link_next:
                    next_url = link_next
                    next_params = None
                    continue

                token_next = self._extract_next_token(response)
                if token_next:
                    next_url = f"{self.BASE_URL}/accounts/{account_hash}/transactions"
                    next_params = {**base_params, "nextPageToken": token_next}
                    continue

                next_url = None

        return all_transactions

    @staticmethod
    def _format_transactions_datetime(value: datetime) -> str:
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        dt = dt.astimezone(UTC)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    @staticmethod
    def _extract_next_link(link_header: str | None) -> str | None:
        if not link_header:
            return None

        for part in link_header.split(","):
            token = part.strip()
            if 'rel="next"' not in token and "rel=next" not in token:
                continue
            if "<" not in token or ">" not in token:
                continue
            start = token.find("<") + 1
            end = token.find(">", start)
            if end <= start:
                continue
            return token[start:end]
        return None

    @staticmethod
    def _extract_next_token(response: httpx.Response) -> str | None:
        body_token_keys = ("nextPageToken", "next_page_token", "nextToken", "next")
        headers_token_keys = (
            "next-page-token",
            "x-next-page-token",
            "schwab-next-page-token",
            "schwab-next-page",
        )

        for key in headers_token_keys:
            value = response.headers.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        payload = response.json()
        if isinstance(payload, dict):
            for key in body_token_keys:
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return None

    @staticmethod
    def _page_key(url: str, params: dict[str, str] | None) -> str:
        if not params:
            return url
        ordered = "&".join(f"{key}={value}" for key, value in sorted(params.items()))
        return f"{url}?{ordered}"
