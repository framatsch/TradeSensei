## ADDED Requirements

### Requirement: CacheService key generation is deterministic
The system SHALL produce identical cache keys for identical inputs regardless of dict key insertion order.

#### Scenario: Canonical JSON sorts keys
- **WHEN** two filter_config dicts with the same data but different key order are passed to `analytics_key`
- **THEN** both calls return the same cache key string

#### Scenario: Different filter configs produce different keys
- **WHEN** two different filter_config dicts are passed to `analytics_key`
- **THEN** the returned keys differ

### Requirement: CacheService no-op fallback works without Redis
The system SHALL silently skip cache reads/writes when REDIS_URL is not configured.

#### Scenario: get returns None with no Redis
- **WHEN** `CacheService().get(key)` is called and `settings.redis_url` is None
- **THEN** the method returns `None` without raising

#### Scenario: set is a no-op with no Redis
- **WHEN** `CacheService().set(key, value)` is called and `settings.redis_url` is None
- **THEN** the method returns without raising

#### Scenario: invalidate_portfolio is a no-op with no Redis
- **WHEN** `CacheService().invalidate_portfolio(portfolio_id, user_id)` is called and Redis is unavailable
- **THEN** the method returns without raising

### Requirement: CacheService interacts with Redis when configured
The system SHALL call `redis.get` and `redis.set` with the correct key and serialised value when a Redis URL is configured.

#### Scenario: get calls redis get
- **WHEN** `CacheService().get(key)` is called with Redis available (mocked)
- **THEN** `redis_client.get(key)` is called exactly once

#### Scenario: set calls redis setex
- **WHEN** `CacheService().set(key, value, ttl)` is called with Redis available (mocked)
- **THEN** `redis_client.setex` is called with the correct key and serialised value
