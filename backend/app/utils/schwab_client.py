"""HTTP client for the Schwab OAuth 2.0 + REST API.

Provides :class:`SchwabClient` which handles PKCE authorization URL
construction, authorization-code exchange, token refresh, and order
retrieval.  All network calls use ``httpx``.
"""

from __future__ import annotations

import urllib.parse
from typing import Any

import httpx

from app.core.config import settings
from app.core.exceptions import ConfigurationError


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

    BASE_URL: str = "https://api.schwab.com/v1"
    AUTH_URL: str = "https://api.schwab.com/v1/oauth/authorize"
    TOKEN_URL: str = "https://api.schwab.com/v1/oauth/token"  # noqa: S105

    def _require_client_id(self) -> str:
        """Return the Schwab client ID, raising if not configured.

        Returns:
            The ``SCHWAB_CLIENT_ID`` string.

        Raises:
            :class:`~app.core.exceptions.ConfigurationError`: If
                ``settings.schwab_client_id`` is ``None``.
        """
        client_id = settings.schwab_client_id
        if not client_id:
            raise ConfigurationError("SCHWAB_CLIENT_ID is not configured. Set the SCHWAB_CLIENT_ID environment variable to enable Schwab integration.")
        return client_id

    def get_authorization_url(self, state: str, code_challenge: str) -> str:
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

        Raises:
            :class:`~app.core.exceptions.ConfigurationError`: If
                ``SCHWAB_CLIENT_ID`` is not configured.
        """
        client_id = self._require_client_id()
        params: dict[str, str] = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": settings.schwab_redirect_uri,
            "scope": "readonly",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return f"{self.AUTH_URL}?{urllib.parse.urlencode(params)}"

    async def exchange_code(
        self,
        code: str,
        code_verifier: str,
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
            :class:`~app.core.exceptions.ConfigurationError`: If
                ``SCHWAB_CLIENT_ID`` or ``SCHWAB_CLIENT_SECRET`` are not set.
            :class:`httpx.HTTPStatusError`: If the token endpoint returns a
                non-2xx response.
        """
        client_id = self._require_client_id()
        client_secret = settings.schwab_client_secret
        if not client_secret:
            raise ConfigurationError("SCHWAB_CLIENT_SECRET is not configured. Set the SCHWAB_CLIENT_SECRET environment variable.")
        payload: dict[str, str] = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.schwab_redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
            "code_verifier": code_verifier,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(self.TOKEN_URL, data=payload)
            response.raise_for_status()
            result: dict[str, Any] = response.json()
            return result

    async def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        """Use a refresh token to obtain a new access token.

        Args:
            refresh_token: A valid Schwab OAuth refresh token.

        Returns:
            A dictionary containing at minimum ``access_token`` and
            ``expires_in`` keys.

        Raises:
            :class:`~app.core.exceptions.ConfigurationError`: If
                ``SCHWAB_CLIENT_ID`` or ``SCHWAB_CLIENT_SECRET`` are not set.
            :class:`httpx.HTTPStatusError`: If the token endpoint returns a
                non-2xx response.
        """
        client_id = self._require_client_id()
        client_secret = settings.schwab_client_secret
        if not client_secret:
            raise ConfigurationError("SCHWAB_CLIENT_SECRET is not configured. Set the SCHWAB_CLIENT_SECRET environment variable.")
        payload: dict[str, str] = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(self.TOKEN_URL, data=payload)
            response.raise_for_status()
            result: dict[str, Any] = response.json()
            return result

    async def get_orders(
        self,
        access_token: str,
        from_date: str,
        to_date: str,
    ) -> list[dict[str, Any]]:
        """Fetch orders from the Schwab API for a given date range.

        Args:
            access_token: A valid Schwab OAuth access token.
            from_date: ISO-8601 date string for the start of the range
                (e.g. ``"2024-01-01"``).
            to_date: ISO-8601 date string for the end of the range
                (e.g. ``"2024-01-31"``).

        Returns:
            A list of raw order dictionaries as returned by Schwab.

        Raises:
            :class:`~app.core.exceptions.ConfigurationError`: If
                ``SCHWAB_CLIENT_ID`` is not configured.
            :class:`httpx.HTTPStatusError`: If the orders endpoint returns a
                non-2xx response.
        """
        self._require_client_id()
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {"fromEnteredTime": from_date, "toEnteredTime": to_date}
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/orders",
                headers=headers,
                params=params,
            )
            response.raise_for_status()
            result: list[dict[str, Any]] = response.json()
            return result
