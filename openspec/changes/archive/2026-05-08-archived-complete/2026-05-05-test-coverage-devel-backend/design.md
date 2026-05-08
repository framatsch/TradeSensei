## Context

The `devel` branch adds ~35 new/modified source files covering: daily check-in system, analytics + attribution services, saved dashboard views, cache service (optional Redis), PAT authentication, MCP SSE transport, S3-compatible object storage, and screenshot upload API. Coverage is currently 73.61%. No new production code is needed — only tests.

Existing tests use `pytest-asyncio`, `httpx.AsyncClient` (against a real in-memory test DB with RLS), and `unittest.mock.AsyncMock`/`patch` for external dependencies. All tests live in `backend/tests/`.

## Goals / Non-Goals

**Goals:**
- Write pytest tests covering happy paths, error paths, ownership/auth guards for all new services and API endpoints introduced in `devel`
- Increase overall backend coverage from 73.61% to ≥ 78%
- Use mocks for external calls (boto3, Redis) so CI never requires real infrastructure
- Follow existing test file naming convention: `test_<feature>_<layer>.py`

**Non-Goals:**
- No production code changes
- No frontend tests
- No test infrastructure changes (no new fixtures/conftest additions beyond what's necessary)
- Achieving 100% coverage on any single module is not required — focus on critical paths

## Decisions

### Decision 1: One test file per new feature area (not per class)
**Rationale**: The existing codebase groups tests by feature (e.g. `test_daily_checkin_service.py`, `test_daily_checkins_api.py`) rather than by class. Preserving this makes discoverability consistent.
**Alternative**: One file per class. Rejected — creates too many small files that mirror module structure instead of user-visible behavior.

### Decision 2: Mock Redis and boto3 at the module boundary using `unittest.mock.patch`
**Rationale**: Tests should not require a running Redis or S3 server. Mocking at `app.services.cache_service.redis.asyncio.from_url` and `boto3.client` ensures CI portability.
**Alternative**: Use a testcontainer for Redis. Rejected — adds CI infrastructure complexity that isn't justified for the cache layer which already has a no-op fallback.

### Decision 3: Use the existing `AsyncClient` + real test DB pattern for API integration tests
**Rationale**: All existing API tests use `httpx.AsyncClient` wired to the FastAPI app with a real async DB session (TimescaleDB in test mode). This gives the highest confidence and reuses existing fixtures.
**Alternative**: Pure unit tests with mocked repos. Rejected — the existing integration test suite is the baseline expectation; pure unit tests would add minimal incremental coverage.

### Decision 4: Target 78% overall coverage
**Rationale**: From 73.61% baseline, adding ~9 new test files with thorough coverage of new code should yield ≥ 4.5 pp improvement. 78% is achievable without writing exhaustive edge-case tests for every branch.

## Risks / Trade-offs

- [boto3 mock drift] `StorageService` mocks could diverge from real boto3 behavior → Mitigation: pin the exact method signature (`generate_presigned_url`) and assert call args
- [Redis async mock complexity] `redis.asyncio` client has async methods → Mitigation: use `AsyncMock` for `get`, `set`, `delete` return values
- [Daily check-in seeded data] Tests that verify seeded defaults (from migration `c5d8e9f2a311`) must run in the correct migration order → Mitigation: rely on existing `test_migrations.py` infrastructure; use fresh per-test data where possible
- [Coverage measurement] Lines in newly added files that are never imported under test will lower the coverage delta → Mitigation: ensure every new test file imports its subject module directly
