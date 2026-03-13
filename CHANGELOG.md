# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- [backend] `User` SQLAlchemy ORM model with hashed password and email fields (`backend/app/models/user.py`)
- [backend] `Account` SQLAlchemy ORM model with broker type, balance, and user FK (`backend/app/models/account.py`)
- [backend] `account_id` nullable FK on `Trade` model linking trades to accounts (`backend/app/models/trade.py`)
- [backend] Pydantic v2 schemas `UserCreate`, `UserUpdate`, `UserRead`, `AccountCreate`, `AccountUpdate`, `AccountRead`, `TokenResponse`, `LoginRequest` (`backend/app/schemas/`)
- [backend] JWT authentication endpoints `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `POST /api/v1/auth/refresh` (`backend/app/api/v1/auth.py`)
- [backend] Users REST API `GET/PATCH /api/v1/users/me` and admin list (`backend/app/api/v1/users.py`)
- [backend] Accounts REST API `POST/GET/PATCH/DELETE /api/v1/accounts` scoped to authenticated user (`backend/app/api/v1/accounts.py`)
- [backend] `UserRepository` and `AccountRepository` with async CRUD (`backend/app/repositories/`)
- [backend] `AuthService`, `UserService`, `AccountService` business logic (`backend/app/services/`)
- [backend] JWT/password security utilities (`backend/app/core/security.py`)
- [backend] `get_current_user` FastAPI dependency injection (`backend/app/core/deps.py`)
- [backend] Alembic migration 0002 adding `users` and `accounts` tables with indexes (`backend/alembic/versions/0002_users_accounts_auth.py`)
- [backend] python-jose, passlib, bcrypt runtime dependencies
- [backend] Unit + API tests for auth, users, accounts, and security (5 new test files, 50+ tests)
- [backend] Pure metrics utility functions: win rate, profit factor, max drawdown, expectancy, Sharpe ratio, return distribution (`backend/app/utils/metrics.py`)
- [backend] `MetricsRepository` with async equity curve and closed-trade queries (`backend/app/repositories/metrics_repository.py`)
- [backend] `MetricsService` orchestrating repository queries and statistical calculations (`backend/app/services/metrics_service.py`)
- [backend] Metrics Pydantic schemas: `MetricsSummary`, `EquityCurvePoint`, `DrawdownPoint`, `ReturnDistribution` (`backend/app/schemas/metrics.py`)
- [backend] Metrics endpoints `GET /api/v1/metrics/summary`, `/equity-curve`, `/drawdown`, `/distribution` scoped to authenticated user's accounts (`backend/app/api/v1/metrics.py`)
- [backend] Unit tests for metrics utility functions and metrics service (2 new test files)
- [backend] Abstract `BrokerParser` base class for file import parsers (`backend/app/utils/parsers/base.py`)
- [backend] `IBKRParser`: IBKR Activity Statement CSV parser locating the Trades section, mapping asset classes, handling direction from quantity sign (`backend/app/utils/parsers/ibkr.py`)
- [backend] `SchwabParser`: Schwab trade history CSV parser with named column validation and dollar-sign stripping (`backend/app/utils/parsers/schwab.py`)
- [backend] `get_parser()` factory keyed by `BrokerType` StrEnum (`ibkr` | `schwab`) (`backend/app/utils/parsers/factory.py`)
- [backend] `ImportService` orchestrating account ownership check, file parsing, and bulk trade creation (`backend/app/services/import_service.py`)
- [backend] `POST /api/v1/imports/upload` multipart endpoint with file size validation (10 MB limit), format check, 413/400/404 error responses, and auth guard (`backend/app/api/v1/imports.py`)
- [backend] `ImportResult` Pydantic response schema with import statistics and per-row warnings (`backend/app/schemas/imports.py`)
- [backend] `account_id` optional field added to `TradeCreate` schema for import stamping
- [backend] openpyxl runtime + types-openpyxl dev dependencies for Excel file support
- [backend] 44 unit tests covering parsers, import service, and import API layer

### FastAPI application factory with CORS middleware (`backend/app/main.py`)
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
