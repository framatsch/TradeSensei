## 1. Database — Portfolio Model & Migration

- [ ] 1.1 Create `backend/app/models/portfolio.py` — `Portfolio` ORM model with columns: `id` (UUID PK), `user_id` (FK → users.id CASCADE), `name` (String 100), `base_currency` (String 3), `is_paper` (Boolean default False), `color_hex` (String 7, nullable), `created_at`, `updated_at`
- [ ] 1.2 Add `Portfolio` to `backend/app/models/__init__.py` exports
- [ ] 1.3 Add `portfolio_id` (UUID FK → portfolios.id, nullable initially) to `Account` ORM model in `backend/app/models/account.py`; add `portfolio` relationship (many:1)
- [ ] 1.4 Write Alembic migration `XXXX_add_portfolio_model.py`:
  - Step 1: `CREATE TABLE portfolios` with all columns and `CHECK (color_hex ~ '^#[0-9A-Fa-f]{6}$')`
  - Step 2: `CREATE INDEX ix_portfolios_user_id` on `portfolios(user_id)`
  - Step 3: `ALTER TABLE accounts ADD COLUMN portfolio_id UUID NULLABLE REFERENCES portfolios(id)`
  - Step 4: `CREATE INDEX ix_accounts_portfolio_id` on `accounts(portfolio_id)`
  - Step 5: Data backfill — insert one `"Default Portfolio"` per user (base_currency='USD', is_paper=False, color_hex='#6366f1'), then `UPDATE accounts SET portfolio_id = ...`
  - Step 6: `ALTER TABLE accounts ALTER COLUMN portfolio_id SET NOT NULL`
  - Downgrade: reverse all steps including nullifying `portfolio_id` before dropping `portfolios`
- [ ] 1.5 Verify migration locally with `alembic upgrade head` and `alembic downgrade -1`

## 2. Pydantic Schemas — Portfolio

- [ ] 2.1 Create `backend/app/schemas/portfolio.py` with:
  - `PortfolioCreate` — `name` (str, max 100), `base_currency` (str, 3-char allowlist), `is_paper` (bool), `color_hex` (str, optional, regex validated)
  - `PortfolioUpdate` — all fields optional; same validators as Create
  - `PortfolioRead` — id, user_id, name, base_currency, is_paper, color_hex, created_at, updated_at
- [ ] 2.2 Add `portfolio_id` (UUID) to `AccountCreate` and `AccountRead` in `backend/app/schemas/account.py`
- [ ] 2.3 Export new schemas from `backend/app/schemas/__init__.py`

## 3. Repository Layer — Portfolio

- [ ] 3.1 Create `backend/app/repositories/portfolio.py` with:
  - `get_by_id(db, portfolio_id, user_id) → Portfolio | None`
  - `list_by_user(db, user_id) → list[Portfolio]`
  - `create(db, user_id, data: PortfolioCreate) → Portfolio`
  - `update(db, portfolio, data: PortfolioUpdate) → Portfolio`
  - `delete(db, portfolio) → None`
  - `has_trades(db, portfolio_id) → bool` — checks if any trade exists whose account links to this portfolio
  - `has_accounts(db, portfolio_id) → bool` — checks account count > 0
- [ ] 3.2 Update `backend/app/repositories/account.py`:
  - `get_by_id` must additionally verify `account.portfolio.user_id == user_id`
  - `list_by_user` optionally filters by `portfolio_id`
  - `create` accepts `portfolio_id` and validates it belongs to `user_id`
- [ ] 3.3 Update `backend/app/repositories/trade.py`:
  - All query methods accept `portfolio_id` parameter
  - Add a JOIN/subquery ensuring `trade.account.portfolio_id = portfolio_id AND portfolio.user_id = user_id`
- [ ] 3.4 Update `backend/app/repositories/metrics.py` (or equivalent query builders) to accept and enforce `portfolio_id` in all aggregation queries
- [ ] 3.5 Update `backend/app/repositories/cash_transaction.py` to accept `portfolio_id` and verify account membership

## 4. Service Layer — Portfolio

- [ ] 4.1 Create `backend/app/services/portfolio_service.py` with:
  - `create_portfolio(db, user_id, data)` — validates name uniqueness, creates record
  - `get_portfolio(db, portfolio_id, user_id)` — raises 404 if not owned
  - `list_portfolios(db, user_id) → list[PortfolioRead]`
  - `update_portfolio(db, portfolio_id, user_id, data)` — validates `base_currency` immutability if `has_trades`; validates `name` uniqueness
  - `delete_portfolio(db, portfolio_id, user_id)` — raises 409 if `has_accounts`
- [ ] 4.2 Update `backend/app/services/account_service.py`:
  - `create_account` validates `portfolio_id` exists and belongs to `user_id`
- [ ] 4.3 Update `backend/app/services/metrics_service.py`:
  - All public methods accept `portfolio_id`; pass to repository
- [ ] 4.4 Update `backend/app/services/timeseries_service.py`:
  - All public methods accept `portfolio_id`; pass to repository
- [ ] 4.5 Update `backend/app/services/import_service.py`:
  - `import_file` / `import_flex` accept `portfolio_id`
  - Validate that target `account_id` belongs to `portfolio_id`
  - Emit `currency_mismatch` warning when imported trade currency ≠ portfolio `base_currency`

## 5. API Routers — Portfolio CRUD

- [ ] 5.1 Create `backend/app/api/v1/portfolios.py` router (prefix `/portfolios`):
  - `GET /portfolios` → `list_portfolios`
  - `POST /portfolios` → `create_portfolio` (201)
  - `GET /portfolios/{portfolio_id}` → `get_portfolio`
  - `PATCH /portfolios/{portfolio_id}` → `update_portfolio`
  - `DELETE /portfolios/{portfolio_id}` → `delete_portfolio` (204)
- [ ] 5.2 Register `portfolios` router in `backend/app/api/v1/__init__.py`

## 6. API Routers — Portfolio-Scoped Existing Endpoints

- [ ] 6.1 Re-mount `trades` router under `/portfolios/{portfolio_id}/trades`; update all handlers to extract `portfolio_id` from path and pass to service
- [ ] 6.2 Re-mount `executions` router under `/portfolios/{portfolio_id}`; update handlers
- [ ] 6.3 Re-mount `metrics` router under `/portfolios/{portfolio_id}/metrics`; update handlers
- [ ] 6.4 Re-mount `timeseries` router under `/portfolios/{portfolio_id}/timeseries`; update handlers
- [ ] 6.5 Re-mount `imports` router under `/portfolios/{portfolio_id}/imports`; update handlers
- [ ] 6.6 Re-mount `accounts` router under `/portfolios/{portfolio_id}/accounts`; update handlers
- [ ] 6.7 Re-mount `cash_transactions` router under `/portfolios/{portfolio_id}/accounts/{account_id}/cash-transactions`; update handlers
- [ ] 6.8 Add HTTP 410 Gone responses on all old (pre-portfolio) URL patterns with deprecation message pointing to the new paths

## 7. Ownership & Isolation Enforcement

- [ ] 7.1 Create helper `get_portfolio_or_404(portfolio_id, user_id, db)` as a FastAPI dependency in `backend/app/core/dependencies.py`
- [ ] 7.2 Ensure all repository join chains are correct: `trade → account → portfolio` and `portfolio.user_id = user_id`
- [ ] 7.3 Verify `account_id` query-param scoping in metrics/timeseries: if `account_id` provided, verify it belongs to `portfolio_id` (return HTTP 400 if not)
- [ ] 7.4 Add `portfolio` to `AccountRead` response schema (return `portfolio_id` and `portfolio_name`)
- [ ] 7.5 Extend `TradeRead` to include `portfolio_id` field (via account FK chain or denormalised)

## 8. Tests

- [ ] 8.1 Unit tests for `PortfolioRepository` — CRUD operations, uniqueness enforcement, `has_trades`, `has_accounts`
- [ ] 8.2 Unit tests for `PortfolioService` — `base_currency` immutability guard, deletion conflict guard, name uniqueness
- [ ] 8.3 Integration tests for portfolio CRUD endpoints — create, list, get, patch, delete; all ownership scenarios (own/foreign/missing)
- [ ] 8.4 Integration tests for portfolio-scoped trade endpoints — verify isolation: trade from another portfolio returns 404
- [ ] 8.5 Integration tests for portfolio-scoped metrics/timeseries — verify data does not leak across portfolios
- [ ] 8.6 Integration tests for import with currency mismatch warning
- [ ] 8.7 Update all existing test fixtures to create a default portfolio and link accounts to it (factory/conftest changes in `backend/tests/`)
- [ ] 8.8 Verify migration script: write a pytest test that runs `alembic upgrade head` + `alembic downgrade -1` on a fresh DB without errors

## 9. OpenAPI Sync & Lint

- [ ] 9.1 Run `openapi-sync` skill to regenerate the TypeScript client after all endpoint changes
- [ ] 9.2 Run `lint-check` skill (`ruff check`, `ruff format`, `mypy --strict`) and fix all errors
- [ ] 9.3 Run `unit-test` skill (`pytest`) and verify all tests pass

## 10. Documentation & Changelog

- [ ] 10.1 Update `AGENTS.md` iteration table — add iteration 9 row for Portfolio model
- [ ] 10.2 Update `docs/dev-guide.md` with new portfolio concept, new URL structure, and migration notes
- [ ] 10.3 Append to `CHANGELOG.md` under `[Unreleased]`:
  - Added: `Portfolio` entity (id, name, base_currency, is_paper, color_hex)
  - Added: CRUD endpoints for portfolios at `/api/v1/portfolios`
  - Changed: All trade, metrics, timeseries, import, and cash-transaction endpoints are now scoped under `/api/v1/portfolios/{portfolio_id}`
  - Migration: default portfolio created for every existing user; all accounts migrated automatically
