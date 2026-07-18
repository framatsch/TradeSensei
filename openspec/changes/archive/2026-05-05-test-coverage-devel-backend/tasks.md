## 1. Cache Service Tests

- [x] 1.1 Create `backend/tests/test_cache_service.py` with unit tests for `CacheService.analytics_key` determinism (key sorting)
- [x] 1.2 Add tests for `CacheService.analytics_key` producing different keys for different filter configs
- [x] 1.3 Add tests for no-op fallback: `get`, `set`, `invalidate_portfolio` all return without raising when Redis URL is absent
- [x] 1.4 Add tests for Redis-enabled path using `AsyncMock` patch on `redis.asyncio.from_url`: `get` calls `redis.get`, `set` calls `redis.setex`

## 2. Analytics Service Tests

- [x] 2.1 Create `backend/tests/test_analytics_service.py` with unit tests for `AnalyticsService.get_summary` cache-hit path (repo not called)
- [x] 2.2 Add test for cache-miss path: repository is called and `CacheService.set` is invoked
- [x] 2.3 Add test for inline `filter_config` routing (no `saved_view_id`)
- [x] 2.4 Add test for `saved_view_id` resolution: view loaded and its filter applied
- [x] 2.5 Add test for unknown `saved_view_id` raising `SavedDashboardViewNotFoundError`
- [x] 2.6 Add integration test for `POST /portfolios/{id}/analytics/summary` (200 for owner, 403 for non-owner)

## 3. Attribution Service Tests

- [x] 3.1 Create `backend/tests/test_attribution_service.py` with unit test for cache-hit path skipping repository call
- [x] 3.2 Add unit test for `Spec5NotDeployedError` propagation
- [x] 3.3 Add integration test for `GET /portfolios/{id}/analytics/correlations/market-phase` (200 for owner, 403 for non-owner)

## 4. Saved Dashboard View Tests

- [x] 4.1 Create `backend/tests/test_views_api.py` with integration test for `POST /portfolios/{id}/views` (201 for owner, 403 for non-owner)
- [x] 4.2 Add test for `GET /portfolios/{id}/views` listing
- [x] 4.3 Add test for `GET /portfolios/{id}/views/{view_id}` by ID (200 for known, 404 for unknown)
- [x] 4.4 Add test for `PATCH /portfolios/{id}/views/{view_id}` updating name
- [x] 4.5 Add test for `DELETE /portfolios/{id}/views/{view_id}` (204, view gone)

## 5. Daily Check-in Field & Phase Tests

- [x] 5.1 Extend `backend/tests/test_checkin_fields.py` (or create new) with tests for `GET /checkin-fields` and `POST /checkin-fields`
- [x] 5.2 Add test for `DELETE /checkin-fields/{id}` (204 success, 404 for unknown)
- [x] 5.3 Create `backend/tests/test_market_phases_api.py` with tests for `GET /market-phases`, `POST /market-phases`, and duplicate label 409
- [x] 5.4 Add unit test for `DailyCheckinService._validate_target_indices` rejecting unknown index IDs

## 6. Market Index Definition Tests

- [x] 6.1 Create `backend/tests/test_market_indexes_api.py` with tests for `POST /market-indexes` (201) and `GET /market-indexes` (200)
- [x] 6.2 Add test for `PATCH /market-indexes/{id}` (200 with updated data)
- [x] 6.3 Add test for `DELETE /market-indexes/{id}` (204)
- [x] 6.4 Add test for non-owner access returning 404/403

## 7. MCP Transport Tests

- [x] 7.1 Create `backend/tests/test_mcp_api.py` with test for `GET /mcp/sse` missing auth → 401
- [x] 7.2 Add test for `GET /mcp/sse` with invalid PAT → 401
- [x] 7.3 Add test for `GET /mcp/sse` with valid PAT → SSE stream with `event: ready` and `text/event-stream` content type
- [x] 7.4 Add test for invalid `session_id` format → 400
- [x] 7.5 Add test for valid `session_id` echoed in ready event payload
- [x] 7.6 Add test for `POST /mcp/messages` without PAT → 401

## 8. Storage Service Tests

- [x] 8.1 Create `backend/tests/unit/test_storage_service.py` with unit test for `_generate_upload_url` happy path (mocked `boto3.client`)
- [x] 8.2 Add test verifying `boto3.client.generate_presigned_url` is called with `ClientMethod="put_object"` and correct params
- [x] 8.3 Add test for unsupported content type raising `UnsupportedContentTypeError`
- [x] 8.4 Add test for missing `storage_backend` config raising `ConfigurationError`
- [x] 8.5 Add test for empty filename raising `ValueError`

## 9. Screenshot API Tests

- [x] 9.1 Extend `backend/tests/test_trade_image_upload.py` or create `backend/tests/test_screenshots_api.py` with happy-path POST upload test (201, URL in image_urls)
- [x] 9.2 Add test for oversized upload returning 413
- [x] 9.3 Add test for disallowed content type returning 415
- [x] 9.4 Add test for non-owner upload returning 404
- [x] 9.5 Add test for DELETE screenshot removing URL from trade (200)

## 10. Trade Service Cache Invalidation Tests

- [x] 10.1 Add unit/integration tests in `backend/tests/test_trade_service.py` for `bulk_assign_playbook` invalidating cache when `portfolio_id` is set
- [x] 10.2 Add test for `merge_trades` calling `cache.invalidate_portfolio` after merge completes
- [x] 10.3 Add test for `partial_close_trade` invalidating cache via account lookup

## 11. Verification

- [x] 11.1 Run full test suite: `cd backend && uv run pytest --cov=app --cov-report=term-missing -q`
 - [x] 11.2 Confirm overall coverage is ≥ 74%
- [x] 11.3 Fix any test failures from devel branch changes before marking complete
