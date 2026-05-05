## Why

The `devel` branch introduces 35 new/modified backend source files across 6 major feature areas, but no corresponding test files exist for several of them. Current coverage is 73.61% and must increase to ensure correctness and prevent regressions when `devel` is merged to `main`.

## What Changes

- Add unit and integration tests for all new backend capabilities introduced in `devel`:
  - **Daily check-in system** (fields, phases, market-index definitions, check-in CRUD)
  - **Analytics & attribution layer** (analytics service, attribution service, saved dashboard views)
  - **Cache service** (no-op and Redis paths, key generation, invalidation)
  - **Personal access tokens (PAT)** (CRUD, auth via PAT, expiry enforcement) — partial coverage exists; gaps remain
  - **MCP SSE transport** (endpoint guards, keepalive, session-id validation)
  - **Object storage service** (presigned URL generation, content-type guard, missing config guard)
  - **Screenshot upload API** (size limit, type guard, happy path, ownership)
  - **Trade service cache invalidation** (bulk assign playbook, merge trades, partial close)
  - **Market index/phase definitions** (CRUD coverage)

## Capabilities

### New Capabilities
- `cache-service-tests`: Unit tests for `CacheService` covering key building, canonical JSON, no-op fallback, get/set/invalidate with mocked Redis
- `analytics-service-tests`: Service-layer unit tests for `AnalyticsService` summary computation, saved-view resolution, and cache read/write paths
- `attribution-service-tests`: Service-layer unit tests for `AttributionService` market-phase correlation, cache paths, and `Spec5NotDeployedError` handling
- `saved-dashboard-view-tests`: Integration tests for the `/portfolios/{id}/views` CRUD endpoints and `SavedDashboardViewService`
- `daily-checkin-field-tests`: Integration tests for the `/checkin-fields` and `/market-phases` endpoints and their service/repo layers
- `market-index-tests`: Integration tests for `/market-indexes` endpoints and `MarketIndexDefinitionService`
- `mcp-transport-tests`: Unit/integration tests for `/mcp/sse` PAT guard, keepalive, session-id validation, and `/mcp/messages` stub
- `storage-service-tests`: Pure unit tests for `StorageService` presigned-URL logic (mocked boto3), content-type rejection, and config guard
- `screenshot-api-tests`: Integration tests for `POST/DELETE /trades/{id}/screenshots` covering happy path, size limit, type guard, and ownership

### Modified Capabilities
- `self-hosted-object-storage`: Existing spec covers presigned URL design; test coverage needs to be added for the implemented `StorageService`

## Impact

- **New test files** only — no production code changes
- Target: overall coverage ≥ 78% (up from 73.61%)
- All new tests follow existing `pytest-asyncio` + `httpx.AsyncClient` + `AsyncMock` patterns
- boto3 calls must be mocked — no real S3/object-storage calls in CI
- Redis calls must be mocked — no real Redis required in CI
