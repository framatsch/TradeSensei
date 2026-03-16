# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

<!-- Google OAuth login -->

### Added

- [backend] `provider VARCHAR(20) NOT NULL DEFAULT 'local'` and `provider_id VARCHAR(255) NULL` columns on the `users` table; `hashed_password` made nullable to support OAuth-only accounts; Alembic migration `0006_google_oauth_provider_fields` (`backend/alembic/versions/0006_google_oauth_provider_fields.py`)
- [backend] `get_by_provider_id`, `create_oauth_user`, and `link_oauth_account` methods on `UserRepository` for OAuth account resolution and linking (`backend/app/repositories/user_repository.py`)
- [backend] `google_oauth_login` and `exchange_one_time_token` methods on `AuthService`; password login is rejected with `InvalidCredentialsError` for OAuth-only accounts (`backend/app/services/auth_service.py`)
- [backend] One-time token (60 s TTL, single-use) in `backend/app/core/security.py` used to safely transfer the JWT pair across the OAuth callback redirect
- [backend] `GET /api/v1/auth/google` — redirects browser to Google's OAuth authorization URL (`backend/app/api/v1/auth.py`)
- [backend] `GET /api/v1/auth/google/callback` — receives authorization code from Google, issues JWT pair + one-time token, sets refresh cookie, redirects to frontend (`backend/app/api/v1/auth.py`)
- [backend] `POST /api/v1/auth/google/exchange` — accepts one-time token, returns `TokenResponse` (`backend/app/api/v1/auth.py`)
- [backend] `authlib>=1.3` dependency for the server-side OAuth 2.0 client (`backend/pyproject.toml`)
- [frontend] `next-auth@^4` installed; `app/api/auth/[...nextauth]/route.ts` stub handler added for NextAuth session management (`frontend/`)
- [frontend] `GoogleSignInButton` component with official Google brand colours; added to `LoginForm` and `RegisterForm` with a visual divider (`frontend/components/auth/GoogleSignInButton.tsx`)
- [frontend] `OAuthErrorBanner` component displaying user-friendly error messages for OAuth failures (`frontend/components/auth/OAuthErrorBanner.tsx`)
- [frontend] `app/(auth)/auth/callback/page.tsx` — exchanges the one-time token via `POST /api/v1/auth/google/exchange`, stores the access token, and redirects to `/dashboard` (`frontend/app/(auth)/auth/callback/page.tsx`)
- [frontend] `frontend/.env.example` documenting all required environment variables: `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_GOOGLE_CLIENT_ID`, `NEXTAUTH_SECRET`, `NEXTAUTH_URL` (`frontend/.env.example`)
- [backend] Unit tests for `google_oauth_login` (20 cases) and one-time token (21 cases); integration tests for the three OAuth routes (14 cases)

<!-- Iteration 6: Playbook, tagging, and psychological notes -->

### Added

- [backend] `Playbook` model for named trade setup strategies, user-scoped with uniqueness constraint (`backend/app/models/playbook.py`)
- [backend] `Tag` model for trade categorisation with hex color support (`backend/app/models/tag.py`)
- [backend] `TradeTag` many-to-many association table (`backend/app/models/trade_tag.py`)
- [backend] `TradeNote` model for psychological notes with optional emotion field (`backend/app/models/trade_note.py`)
- [backend] Full CRUD `/api/v1/playbooks` and `/api/v1/tags` endpoints (`backend/app/api/v1/`)
- [backend] Nested notes endpoints: `GET/POST /api/v1/trades/{id}/notes`, `PATCH/DELETE /api/v1/trades/{id}/notes/{note_id}` (`backend/app/api/v1/notes.py`)
- [backend] Eager loading of tags and notes on all trade queries via `selectinload` (`backend/app/repositories/trade_repository.py`)
- [backend] Alembic migration `0003`: playbooks, tags, trade_tags, trade_notes tables + playbook_id FK on trades (`backend/alembic/versions/0003_playbook_tags_notes.py`)
- [frontend] Playbooks management page with inline CRUD forms
- [frontend] Tags management page with color picker and `TagBadge` chips
- [frontend] Trade detail page (`/dashboard/trades/[id]`) with `NoteList` and add note form
- [backend] Unit tests for playbook service (9), tag service (9), note service (9) — all 27 passing

<!-- Iteration 5: Time-series endpoints, initial frontend -->

- [backend] Time-series aggregation endpoints: `GET /api/v1/timeseries/daily-pnl`, `/monthly-pnl`, `/pnl-by-symbol`, `/pnl-by-asset-class`, `/return-distribution` (`backend/app/api/v1/timeseries.py`)
- [backend] Pydantic schemas: `DailyPnl`, `MonthlyPnl`, `PnlBySymbol`, `PnlByAssetClass`, `ReturnDistribution` (`backend/app/schemas/timeseries.py`)
- [backend] `TimeSeriesRepository` with user-isolated aggregation queries (`backend/app/repositories/timeseries_repository.py`)
- [backend] `TimeSeriesService` with equal-width histogram computation for return distribution (`backend/app/services/timeseries_service.py`)
- [frontend] Next.js 14 App Router application at `frontend/` with TypeScript strict mode, Tailwind CSS dark theme
- [frontend] Login and registration forms with JWT auth flow and Zustand auth store
- [frontend] Dashboard page with MetricsCards (6 KPIs), EquityCurveChart (Recharts LineChart), DrawdownChart (Recharts AreaChart)
- [frontend] Paginated trade list with cursor-based navigation
- [frontend] Broker file import UI with broker selector, account selector, and ImportResult display
- [frontend] React Query hooks for all data fetching (`frontend/hooks/`)

<!-- Iteration 4: Broker import (IBKR + Schwab) -->

- [backend] IBKR Activity Statement CSV parser (`backend/app/utils/parsers/ibkr.py`)
- [backend] Charles Schwab trade history CSV parser (`backend/app/utils/parsers/schwab.py`)
- [backend] Broker parser factory with `BrokerType` enum (`backend/app/utils/parsers/factory.py`)
- [backend] `POST /api/v1/imports/upload` multipart file upload endpoint with 10 MB size limit (`backend/app/api/v1/imports.py`)
- [backend] `ImportResult` schema with parsed/created/skipped counts and non-fatal warnings (`backend/app/schemas/imports.py`)
- [backend] `ImportService` with account ownership validation before bulk trade creation (`backend/app/services/import_service.py`)
- [backend] Domain exceptions: `ImportParseError`, `UnsupportedBrokerError`

<!-- Iteration 3: Performance metrics and statistical aggregation -->

- [backend] Performance metrics computation: win rate, loss rate, profit factor, expectancy, Sharpe ratio (annualised), max drawdown (`backend/app/utils/metrics.py`)
- [backend] Equity curve and drawdown curve time-series computation (`backend/app/utils/metrics.py`)
- [backend] `GET /api/v1/metrics/summary`, `GET /api/v1/metrics/equity-curve`, `GET /api/v1/metrics/drawdown` endpoints (`backend/app/api/v1/metrics.py`)
- [backend] Pydantic schemas: `TradeMetrics`, `DrawdownPoint`, `EquityCurvePoint`, `MetricsSummary` (`backend/app/schemas/metrics.py`)
- [backend] `MetricsRepository` for user-isolated closed trade retrieval (`backend/app/repositories/metrics_repository.py`)
- [backend] Unit tests for metrics utilities (25) and metrics service (13)

<!-- Iteration 2: User model, Account model, JWT auth (multi-user) -->

- [backend] `User` SQLAlchemy model with bcrypt password hashing and `refresh_token_version` for revocation (`backend/app/models/user.py`)
- [backend] `Account` SQLAlchemy model with user-scoped data isolation (`backend/app/models/account.py`)
- [backend] JWT authentication: access tokens (15 min), httpOnly refresh token cookies (7 days) with rotation and revocation (`backend/app/core/security.py`)
- [backend] `POST /api/v1/auth/register`, `POST /api/v1/auth/token`, `POST /api/v1/auth/refresh`, `POST /api/v1/auth/logout` endpoints (`backend/app/api/v1/auth.py`)
- [backend] `GET/PATCH/DELETE /api/v1/users/me` endpoints (`backend/app/api/v1/users.py`)
- [backend] Full CRUD `/api/v1/accounts` endpoints with user isolation (`backend/app/api/v1/accounts.py`)
- [backend] Domain exceptions: `UserAlreadyExistsError`, `InvalidCredentialsError`, `UserNotFoundError`, `AccountNotFoundError`, `InvalidTokenError` (`backend/app/core/exceptions.py`)
- [backend] `get_current_user` FastAPI dependency with `is_active` guard (`backend/app/core/deps.py`)
- [backend] Alembic migration `0002`: users and accounts tables with updated_at triggers and explicit FK constraint names (`backend/alembic/versions/0002_users_accounts_auth.py`)
- [backend] Unit tests for auth service (12), account service (10), security utilities (16) — all 38 passing

<!-- Iteration 1: Data model, Pydantic schemas, base API + DB -->

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
