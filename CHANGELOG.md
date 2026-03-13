# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- [backend] FastAPI application factory with CORS middleware (`backend/app/main.py`)
- [backend] `Trade` SQLAlchemy ORM model with `Direction` and `AssetClass` enums (`backend/app/models/trade.py`)
- [backend] Pydantic v2 schemas `TradeCreate`, `TradeUpdate`, and `TradeRead` with full field validation including timezone-aware datetimes and cross-field date order validation (`backend/app/schemas/trade.py`)
- [backend] Generic response envelopes `ResponseEnvelope[T]` and `CursorPage[T]` for consistent API responses (`backend/app/schemas/common.py`)
- [backend] `TradeRepository` with async CRUD operations and keyset cursor-based pagination (`backend/app/repositories/trade_repository.py`)
- [backend] `TradeService` business logic layer with domain exceptions (`backend/app/services/trade_service.py`)
- [backend] REST API endpoints `POST /api/v1/trades`, `GET /api/v1/trades`, `GET /api/v1/trades/{id}`, `PATCH /api/v1/trades/{id}`, `DELETE /api/v1/trades/{id}` (`backend/app/api/v1/trades.py`)
- [backend] Domain exception classes `TradeNotFoundError` and `InvalidCursorError` (`backend/app/core/exceptions.py`)
- [backend] pydantic-settings `Settings` class for environment-based configuration (`backend/app/core/config.py`)
- [backend] Async SQLAlchemy engine and session factory with `get_session` FastAPI dependency (`backend/app/core/database.py`)
- [backend] Application constants `PAGINATION_DEFAULT_LIMIT`, `PAGINATION_MAX_LIMIT`, `SYMBOL_MAX_LENGTH`, `SYMBOL_MIN_LENGTH`, `NOTES_MAX_LENGTH` (`backend/app/core/constants.py`)
- [backend] Alembic initial migration creating the `trades` hypertable with TimescaleDB time-series partitioning, indexes, and `updated_at` auto-update trigger (`backend/alembic/versions/0001_initial_schema.py`)
- [backend] Full OpenAPI annotations on all route handlers and `Field(description=...)` on all Pydantic schema fields
- [backend] Unit tests for trade schemas (9 tests) and trade service (9 tests), all passing (`backend/tests/`)
- [infra] Multi-stage Alpine Dockerfile for `dev` and `prod` build targets (`backend/Dockerfile`)
- [infra] GitHub Actions CI workflow covering lint (ruff), type-check (mypy --strict), unit tests (pytest), and migration smoke-test (`alembic upgrade head`) (`.github/workflows/ci.yml`)
- [infra] GitHub Actions Docker workflow for multi-arch builds (amd64/arm64) and push to `ghcr.io` (`.github/workflows/docker.yml`)
- [infra] Docker Compose stacks for local development, CI test isolation, and production (`docker-compose.yml`, `docker-compose.test.yml`, `docker-compose.prod.yml`)
- [infra] Kubernetes manifests covering namespace, backend Deployment/Service/Ingress/ConfigMap, and TimescaleDB StatefulSet/Service (`k8s/`)
- [docs] Project context file `AGENTS.md` with architecture principles, coding guidelines, CI/CD overview, and iteration roadmap
- [docs] Subagent definitions for `backend-engineer`, `frontend-engineer`, `test-writer`, `openapi-docs`, `code-reviewer`, `docs-writer`, `changelog-writer`, and `ui-reviewer` (`.opencode/agents/`)
- [docs] OpenCode skills for `commit-helper`, `lint-check`, `unit-test`, `db-migration`, `openapi-sync`, `deploy-local`, and `docker-build` (`.opencode/skills/`)
- [docs] Developer setup guide (`docs/dev-guide.md`)

[unreleased]: https://github.com/OWNER/tradejournal/compare/HEAD...HEAD
