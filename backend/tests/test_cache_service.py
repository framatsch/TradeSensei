"""Unit tests for cache service behavior with and without Redis."""

import sys
import types
import uuid
from unittest.mock import AsyncMock, Mock

import pytest

from app.core.config import settings
from app.services.cache_service import CacheService


def _install_fake_redis(monkeypatch: pytest.MonkeyPatch, client: AsyncMock) -> Mock:
    from_url = Mock(return_value=client)
    redis_async_module = types.SimpleNamespace(from_url=from_url)
    redis_pkg = types.SimpleNamespace(asyncio=redis_async_module)
    monkeypatch.setitem(sys.modules, "redis", redis_pkg)
    monkeypatch.setitem(sys.modules, "redis.asyncio", redis_async_module)
    return from_url


@pytest.mark.unit
def test_analytics_key_is_deterministic_with_sorted_filter_keys() -> None:
    portfolio_id = uuid.uuid4()
    user_id = uuid.uuid4()

    key_a = CacheService.analytics_key(
        portfolio_id=portfolio_id,
        user_id=user_id,
        filter_config={"currency_mode": "NATIVE", "date_from": "2026-01-01"},
    )
    key_b = CacheService.analytics_key(
        portfolio_id=portfolio_id,
        user_id=user_id,
        filter_config={"date_from": "2026-01-01", "currency_mode": "NATIVE"},
    )

    assert key_a == key_b


@pytest.mark.unit
def test_analytics_key_changes_when_filter_changes() -> None:
    portfolio_id = uuid.uuid4()
    user_id = uuid.uuid4()

    key_a = CacheService.analytics_key(
        portfolio_id=portfolio_id,
        user_id=user_id,
        filter_config={"currency_mode": "NATIVE"},
    )
    key_b = CacheService.analytics_key(
        portfolio_id=portfolio_id,
        user_id=user_id,
        filter_config={"currency_mode": "NORMALIZED", "normalize_to": "EUR"},
    )

    assert key_a != key_b


@pytest.mark.unit
@pytest.mark.asyncio
async def test_noop_fallback_when_redis_url_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "redis_url", None)
    CacheService._logged_missing = False
    service = CacheService()

    assert await service.get("k") is None
    await service.set("k", "v", 60)
    await service.invalidate_portfolio(uuid.uuid4(), uuid.uuid4())


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redis_enabled_get_and_set_use_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis_client = AsyncMock()
    redis_client.get = AsyncMock(return_value="cached-json")
    redis_client.set = AsyncMock(return_value=True)

    from_url = _install_fake_redis(monkeypatch, redis_client)
    monkeypatch.setattr(settings, "redis_url", "redis://localhost:6379/0")
    CacheService._logged_missing = False
    service = CacheService()

    value = await service.get("analytics:key")
    await service.set("analytics:key", "{\"ok\":true}", 300)

    assert value == "cached-json"
    from_url.assert_called_once()
    redis_client.get.assert_awaited_once_with("analytics:key")
    redis_client.set.assert_awaited_once_with("analytics:key", "{\"ok\":true}", ex=300)
