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

"""Unit tests for the /auth/config endpoint's local_auth_enabled logic.

Tests cover:
1. Default: local auth enabled when flag is unset.
2. Disabled: flag set + OIDC configured → local_auth_enabled=False.
3. Disabled: flag set + Google configured → local_auth_enabled=False.
4. Safety guard: flag set but no provider → local_auth_enabled=True (no lockout).
"""

from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.auth import router
from app.core.config import Settings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

app = FastAPI()
app.include_router(router)  # router already carries prefix="/auth"
client = TestClient(app)


def _call_config(settings_overrides: dict) -> dict:  # type: ignore[type-arg]
    """Patch settings and call GET /auth/config, return parsed JSON."""
    base = Settings.model_construct(
        secret_key="test-secret",
        algorithm="HS256",
        access_token_expire_minutes=30,
        refresh_token_expire_days=7,
        database_url="postgresql+asyncpg://x:x@localhost/x",
        google_client_id=None,
        google_client_secret=None,
        oidc_enabled=False,
        oidc_provider_name="OpenID Connect",
        oidc_configuration_url=None,
        oidc_client_id=None,
        oidc_client_secret=None,
        local_auth_disabled=False,
    )
    for k, v in settings_overrides.items():
        object.__setattr__(base, k, v)

    with patch("app.api.v1.auth.settings", base):
        resp = client.get("/auth/config")
    assert resp.status_code == 200
    return resp.json()  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestLocalAuthEnabled:
    def test_default_local_auth_enabled(self) -> None:
        """local_auth_enabled=True when flag is unset (default)."""
        data = _call_config({})
        assert data["local_auth_enabled"] is True

    def test_disabled_with_oidc_configured(self) -> None:
        """local_auth_enabled=False when flag set and OIDC is active."""
        data = _call_config(
            {
                "local_auth_disabled": True,
                "oidc_enabled": True,
                "oidc_configuration_url": "https://auth.example.com/.well-known/openid-configuration",
                "oidc_client_id": "client-id",
                "oidc_client_secret": "client-secret",
            }
        )
        assert data["local_auth_enabled"] is False

    def test_disabled_with_google_configured(self) -> None:
        """local_auth_enabled=False when flag set and Google OAuth is active."""
        data = _call_config(
            {
                "local_auth_disabled": True,
                "google_client_id": "google-id",
                "google_client_secret": "google-secret",
            }
        )
        assert data["local_auth_enabled"] is False

    def test_safety_guard_no_provider(self) -> None:
        """local_auth_enabled=True (safety guard) when flag set but no provider configured."""
        data = _call_config({"local_auth_disabled": True})
        assert data["local_auth_enabled"] is True
