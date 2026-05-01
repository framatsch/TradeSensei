"""Cache abstraction for analytics endpoints with optional Redis backend."""

import hashlib
import json
import logging
import uuid
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Best-effort cache service with a no-op fallback."""

    def __init__(self) -> None:
        self._redis_url = getattr(settings, "redis_url", None)
        self._enabled = bool(self._redis_url)
        self._redis_client: Any | None = None
        if self._enabled:
            try:
                import redis.asyncio as redis_async  # type: ignore[import-not-found]

                self._redis_client = redis_async.from_url(
                    self._redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )
            except Exception:
                self._enabled = False
                logger.warning("REDIS_URL configured but redis client unavailable")
        if not self._enabled:
            logger.warning("REDIS_URL not configured; analytics cache disabled")

    @staticmethod
    def canonical_json(payload: dict[str, object]) -> str:
        """Return canonical JSON string for stable cache hashing."""
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)

    @classmethod
    def analytics_key(
        cls,
        *,
        portfolio_id: uuid.UUID,
        user_id: uuid.UUID,
        filter_config: dict[str, object],
    ) -> str:
        """Build analytics cache key from canonical filter hash."""
        canonical = cls.canonical_json(filter_config)
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return f"analytics:{portfolio_id}:{user_id}:{digest}"

    @classmethod
    def attribution_key(
        cls,
        *,
        portfolio_id: uuid.UUID,
        user_id: uuid.UUID,
        filter_config: dict[str, object],
    ) -> str:
        """Build attribution cache key from canonical filter hash."""
        canonical = cls.canonical_json(filter_config)
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return f"analytics:{portfolio_id}:{user_id}:attribution:{digest}"

    async def get(self, key: str) -> str | None:
        """Retrieve cached JSON payload by key."""
        if not self._enabled:
            return None
        if self._redis_client is None:
            return None
        value = await self._redis_client.get(key)
        return str(value) if value is not None else None

    async def set(self, key: str, value: str, ttl: int) -> None:
        """Store cached JSON payload (TTL ignored in no-op backend)."""
        if not self._enabled:
            return
        if self._redis_client is None:
            return
        await self._redis_client.set(key, value, ex=ttl)

    async def invalidate_portfolio(
        self,
        portfolio_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Invalidate all cache keys for one portfolio and user."""
        if not self._enabled:
            return
        if self._redis_client is None:
            return
        prefix = f"analytics:{portfolio_id}:{user_id}:"
        async for key in self._redis_client.scan_iter(match=f"{prefix}*"):
            await self._redis_client.delete(key)

    async def invalidate_user(self, user_id: uuid.UUID) -> None:
        """Invalidate all cache keys for a user across all portfolios."""
        if not self._enabled:
            return
        if self._redis_client is None:
            return
        async for key in self._redis_client.scan_iter(match=f"analytics:*:{user_id}:*"):
            await self._redis_client.delete(key)
