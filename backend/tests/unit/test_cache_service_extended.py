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

"""Unit tests for CacheService."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.asyncio

_PORTFOLIO_ID = uuid.uuid4()
_USER_ID = uuid.uuid4()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_disabled_service():
    """Return a CacheService with Redis disabled (no URL configured)."""
    from app.services.cache_service import CacheService

    CacheService._logged_missing = False  # reset class-level flag
    with patch("app.services.cache_service.settings") as mock_settings:
        mock_settings.redis_url = None
        svc = CacheService()
    return svc


def _make_enabled_service(redis_client=None):
    """Return a CacheService with a mocked Redis client."""
    from app.services.cache_service import CacheService

    CacheService._logged_missing = False
    svc = CacheService.__new__(CacheService)
    svc._redis_url = "redis://localhost:6379"
    svc._enabled = True
    svc._redis_client = redis_client or AsyncMock()
    return svc


# ---------------------------------------------------------------------------
# Static helpers
# ---------------------------------------------------------------------------


async def test_canonical_json_is_stable():
    from app.services.cache_service import CacheService

    payload1 = {"b": 2, "a": 1}
    payload2 = {"a": 1, "b": 2}
    assert CacheService.canonical_json(payload1) == CacheService.canonical_json(payload2)


async def test_analytics_key_format():
    from app.services.cache_service import CacheService

    key = CacheService.analytics_key(
        portfolio_id=_PORTFOLIO_ID,
        user_id=_USER_ID,
        filter_config={"foo": "bar"},
    )
    assert key.startswith(f"analytics:{_PORTFOLIO_ID}:{_USER_ID}:")


async def test_attribution_key_format():
    from app.services.cache_service import CacheService

    key = CacheService.attribution_key(
        portfolio_id=_PORTFOLIO_ID,
        user_id=_USER_ID,
        filter_config={"foo": "bar"},
    )
    assert "attribution" in key


async def test_analytics_key_differs_for_different_filters():
    from app.services.cache_service import CacheService

    key1 = CacheService.analytics_key(
        portfolio_id=_PORTFOLIO_ID, user_id=_USER_ID, filter_config={"from": "2024-01-01"}
    )
    key2 = CacheService.analytics_key(
        portfolio_id=_PORTFOLIO_ID, user_id=_USER_ID, filter_config={"from": "2024-06-01"}
    )
    assert key1 != key2


# ---------------------------------------------------------------------------
# get / set — disabled backend
# ---------------------------------------------------------------------------


async def test_get_returns_none_when_disabled():
    svc = _make_disabled_service()
    result = await svc.get("some-key")
    assert result is None


async def test_set_is_noop_when_disabled():
    svc = _make_disabled_service()
    # Should not raise
    await svc.set("some-key", "some-value", 300)


async def test_invalidate_portfolio_is_noop_when_disabled():
    svc = _make_disabled_service()
    await svc.invalidate_portfolio(_PORTFOLIO_ID, _USER_ID)


async def test_invalidate_user_is_noop_when_disabled():
    svc = _make_disabled_service()
    await svc.invalidate_user(_USER_ID)


# ---------------------------------------------------------------------------
# get / set — enabled backend
# ---------------------------------------------------------------------------


async def test_get_returns_value_from_redis():
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value="cached-data")
    svc = _make_enabled_service(mock_redis)

    result = await svc.get("my-key")

    assert result == "cached-data"
    mock_redis.get.assert_called_once_with("my-key")


async def test_get_returns_none_when_redis_returns_none():
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    svc = _make_enabled_service(mock_redis)

    result = await svc.get("missing-key")

    assert result is None


async def test_set_calls_redis_set():
    mock_redis = AsyncMock()
    svc = _make_enabled_service(mock_redis)

    await svc.set("my-key", "my-value", 300)

    mock_redis.set.assert_called_once_with("my-key", "my-value", ex=300)


async def test_invalidate_portfolio_deletes_matching_keys():
    mock_redis = AsyncMock()

    key1 = f"analytics:{_PORTFOLIO_ID}:{_USER_ID}:abc123"
    key2 = f"analytics:{_PORTFOLIO_ID}:{_USER_ID}:def456"

    async def _fake_scan_iter(match):
        for k in [key1, key2]:
            yield k

    mock_redis.scan_iter = _fake_scan_iter
    mock_redis.delete = AsyncMock()
    svc = _make_enabled_service(mock_redis)

    await svc.invalidate_portfolio(_PORTFOLIO_ID, _USER_ID)

    assert mock_redis.delete.call_count == 2


async def test_invalidate_user_deletes_matching_keys():
    mock_redis = AsyncMock()
    key1 = f"analytics:some-portfolio:{_USER_ID}:abc"
    key2 = f"analytics:other-portfolio:{_USER_ID}:def"

    async def _fake_scan_iter(match):
        for k in [key1, key2]:
            yield k

    mock_redis.scan_iter = _fake_scan_iter
    mock_redis.delete = AsyncMock()
    svc = _make_enabled_service(mock_redis)

    await svc.invalidate_user(_USER_ID)

    assert mock_redis.delete.call_count == 2


async def test_get_returns_none_when_redis_client_is_none():
    from app.services.cache_service import CacheService

    svc = CacheService.__new__(CacheService)
    svc._enabled = True
    svc._redis_client = None

    result = await svc.get("key")
    assert result is None


async def test_set_noop_when_redis_client_is_none():
    from app.services.cache_service import CacheService

    svc = CacheService.__new__(CacheService)
    svc._enabled = True
    svc._redis_client = None

    # Should not raise
    await svc.set("key", "value", 300)
