---
name: unit-test
description: Run backend unit and integration tests with pytest via uv, including coverage reporting
license: MIT
compatibility: opencode
metadata:
  toolchain: uv, pytest, pytest-asyncio, httpx
  runner: python tools/unit_test.py
---

## What I do

Run the backend test suite with proper coverage targets and help interpret
failing tests by understanding the test architecture.

## Test architecture

| Layer | Location | DB access | What to mock |
|-------|----------|-----------|-------------|
| Unit | `tests/unit/` | None | Repository methods via `AsyncMock` |
| Integration | `tests/integration/` | Real PostgreSQL | Nothing — uses test fixtures |

## When to use me

- After implementing a new feature to verify all tests still pass
- When debugging a failing test
- Before opening a PR (equivalent to the `test` CI job)

## Prerequisites

Integration tests require a running TimescaleDB instance:

```bash
# Start the test DB (from repo root)
docker compose -f docker-compose.test.yml up -d db

# Verify it's healthy
docker compose -f docker-compose.test.yml ps
```

Set the test database URL:
```bash
export DATABASE_URL=postgresql+asyncpg://tradejournal:tradejournal@localhost:5433/tradejournal_test
```

## How to run

```bash
# All tests with coverage
python tools/unit_test.py

# Unit tests only (no DB needed)
python tools/unit_test.py --unit

# Integration tests only
python tools/unit_test.py --integration

# HTML coverage report
python tools/unit_test.py --coverage
# → open backend/htmlcov/index.html

# CI mode (XML output, exits 1 on < 80% coverage)
python tools/unit_test.py --ci
```

Or directly via uv from `backend/`:

```bash
uv run pytest tests/ -v --cov=app --cov-report=term-missing --cov-fail-under=80
```

## Coverage targets

| Module | Minimum |
|--------|---------|
| `app/services/` | 80% |
| `app/schemas/` | 80% |
| `app/repositories/` | 70% (covered by integration tests) |
| `app/api/` | 70% (covered by integration tests) |

## Test fixtures (conftest.py)

Key fixtures provided in `backend/tests/conftest.py`:

```python
async_engine      # Creates all tables against test DB
async_session     # Rolls back after each test automatically
test_client       # httpx.AsyncClient with DB dependency overridden
sample_trade      # Pre-inserted Trade instance
authenticated_headers  # JWT bearer token for a test user
```

## Interpreting failures

- `sqlalchemy.exc.InterfaceError` — DB not running, check docker compose
- `AssertionError: assert 422` — Pydantic validation error, print `response.json()` to see which field
- `ImportError` — missing `uv sync` after a dependency change
