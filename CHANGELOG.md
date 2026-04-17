# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- [frontend] Resolved TypeScript build error in `TradeForm`: removed `.transform()` from the optional `currency` Zod field (caused output/input type mismatch with `zodResolver`) and moved `.toUpperCase()` into `onSubmit`.

## [0.15.0] - 2026-04-18

### Fixed
- [infra] Renamed workspace member in `uv.lock` from `tradejournal-backend` to `tradesensei-backend`, fixing Docker image builds that failed with `--frozen` after the app rename.

## [0.14.0] - 2026-04-18

### Added
- [backend] Introduced `simplified-execution-model`: `LogicalExecution` now tracks `origin` (`imported|manual|merged|split`), `deleted` (soft-delete flag), `user_modified`, and `parent_id` fields instead of the former `status` enum.
- [backend] Soft-delete for imported/merged/split executions: `DELETE /executions/{id}` returns 200 with body; manual executions are hard-deleted (204 No Content).
- [backend] `POST /executions/{id}/restore` endpoint: un-deletes a soft-deleted execution and re-aggregates the parent trade.
- [backend] `POST /executions/{id}/split` endpoint: splits one execution into two child executions with `origin='split'` and the original soft-deleted.
- [backend] `POST /imports/{account_id}/fresh-start` endpoint: deletes all executions and trades for an account within a single transaction, then re-imports from the provided file.
- [backend] `GET /trades/{id}/executions` and `GET /executions` support `?include_deleted=true` to show soft-deleted rows.
- [backend] `PATCH /broker-raw-transactions/{id}/suppress` endpoint to toggle the `suppressed` flag on raw transactions, preventing re-import.
- [backend] Configurable `statement_timeout` guard (default 60 s) on the fresh-start endpoint via `FRESH_START_TIMEOUT` env var.
- [backend] Alembic migration to drop the deprecated `has_conflict` column from the `trades` table.
- [backend] Alembic migration to add `deleted`, `user_modified`, `parent_id`, `origin` columns and supporting indexes to `logical_executions`.
- [frontend] `ExecutionStatusBadge` component derives its color from `origin` + `deleted` + `user_modified` (Imported=blue, Edited=amber, Manual=violet, Merged=orange, Split=cyan, Deleted=gray).
- [frontend] `ExecutionLegsTable` "Show deleted" toggle; deleted rows rendered at 50% opacity with a Restore button.
- [frontend] `SplitExecutionModal` for splitting a single execution into two, with qty/price/timestamp fields and a live preview.
- [frontend] Fresh Start section in the Import dialog, gated behind an explicit acknowledgement checkbox.
- [frontend] `useRestoreExecution`, `useSplitExecution`, and updated `useTradeExecutions` React Query hooks.

### Changed
- [backend] `_re_aggregate_trade` now filters to `deleted=False` executions only (Decision 5 of the spec).
- [backend] Merge-trades service uses `passive_deletes=True` on the `logical_executions` relationship and refreshes the ORM collection before deleting non-survivor trades, preventing FK-cascade data loss.
- [backend] `LogicalExecution` SQLAlchemy model uses `Enum(AssetClass/Direction, create_type=False)` to match the pre-existing PostgreSQL enum types.
- [frontend] Removed `has_conflict` badge from `TradeRow` and conflict count badge from the sidebar.
- [frontend] Removed `ConflictBanner` component from the trade detail page.
- [frontend] `ExecutionRow` uses `origin`/`deleted`/`user_modified` fields instead of deprecated `status`.

### Removed
- [backend] `has_conflict` field removed from `Trade` model, `TradeUpdate`/`TradeFilters` schemas, and all repository/API filter logic.
- [backend] `?has_conflict` query parameter removed from `GET /api/v1/trades`.
- [frontend] `useConflictTradeCount` hook removed from `useTrades.ts`.

### Fixed
- [backend] `merge_trades` service now correctly re-aggregates the survivor after reassigning executions by expiring the session-cached collections via `session.refresh` before deleting non-survivor trades.
- [backend] `delete_execution` for manual executions now cascade-deletes the parent trade when it has no remaining active executions.

### Renamed
- Application renamed from **Trade Journal** to **Trade Sensei** across the full stack: package names (`tradesensei-backend`), Docker/K8s resources, database name, API title, session cookie, frontend UI strings, CI/CD image tags, and all documentation.

## [0.10.0] - 2026-04-03

### Added
- [backend] Added `net_pnl` and `net_pnl_eur` fields to the `Trade` model and Pydantic schemas.
- [backend] Created an Alembic migration to calculate `net_pnl` for existing closed trades.
- [backend] Updated the trade aggregator to automatically calculate net P&L and net P&L EUR for closed trades.
- [frontend] Added `net_pnl` and `net_pnl_eur` to the `Trade` interface and aggregation hooks.
- [frontend] Redesigned the `PerformanceAnalysisDashboard` table with themed groupings: Overview, Profit & Loss, Win/Loss, and Averages.
- [frontend] Updated dashboard Insights and Charting to use Net P&L metrics as the primary performance indicator.

### Changed
- [frontend] Improved table visual hierarchy with theme-responsive borders (`#dadbdf` in light, `#29292b` in dark).

## [0.7.0] - 2026-03-28

### Fixed
- [frontend] Fixed Account E2E tests by adding `page.reload()` and count-based assertions for reliable deletion verification.
- [frontend] Stabilized `playwright.config.ts` by fixing `baseURL` and ensuring correct `storageState` inheritance across test projects.
- [frontend] Improved account deletion hook to correctly invalidate `trades` and `stats` caches, ensuring UI consistency.
- [auth] Made frontend redirect URLs configurable for OIDC/OAuth to support diverse deployment environments.

### Changed
- [infra] Updated `ci-green-loop` skill to support local verification via `gh act` before pushing.

## [0.6.0] - 2026-03-28

### Added
- [backend] Added generic OIDC client support via Authlib with configuration through environment variables.
- [backend] Implemented OIDC login, callback, and token exchange endpoints.
- [backend] Added session middleware to FastAPI for OAuth state management.
- [frontend] Added OIDC sign-in button and dynamic auth configuration.
- [frontend] Switched all API calls to relative paths (`/api/proxy`) for better Docker and Kubernetes compatibility.

### Fixed
- [frontend] Updated `OAuthErrorBanner` to be provider-agnostic.
- [frontend] Fixed Next.js proxy to handle OAuth redirects manually by setting `redirect: "manual"`.
- [backend] Forced `email_verified = True` for OIDC to support internal providers like Authentik.

### Changed
- [infra] Renamed `INTERNAL_API_URL` to `API_URL` and removed obsolete `NEXT_PUBLIC_API_URL`, `NEXTAUTH_SECRET`, and `NEXTAUTH_URL` from frontend service.

### Added
- [frontend] Added a collapsible desktop sidebar with drawer mode, persistent state in localStorage, and a floating toggle button for a cleaner workspace. Keyboard shortcut `Cmd/Ctrl + B` toggles the sidebar.

### Fixed
- [frontend] Playbook creation now shows immediately in the list without requiring a second item to be created (optimistic update via `setQueryData`).
- [frontend] Tag creation now shows immediately in the list without requiring a second item to be created (optimistic update via `setQueryData`).
- [frontend] Playbook update and delete now reflect immediately in the UI without requiring a page refresh (optimistic cache update via `setQueryData`).
- [frontend] Tag delete now reflects immediately in the UI without requiring a page refresh (optimistic cache update via `setQueryData`).
- [frontend] Tag filtering in the trades overview now works correctly — uses OR logic so trades with any of the selected tags are returned.
- [frontend] Account filter in the trades overview is now visible for all users, not just those with multiple accounts.
- [backend] Fixed tag filter in `GET /api/v1/trades` — FastAPI's `Depends()` does not parse `list[UUID]` query parameters from Pydantic models; `tag_ids` is now declared as an explicit `Query()` parameter on the endpoint and merged into the filter object before the service call.
- [backend] Fixed 500 Internal Server Error on `/api/v1/metrics/summary` and `/api/v1/metrics/equity-curve` caused by `MissingGreenlet` error in async SQLAlchemy when Pydantic serialized unloaded relationships (`playbook`, `tags`, `trade_notes`). All required relationships are now eagerly loaded via `selectinload`.

## [0.5.1] - 2026-03-26

### Added
- [infra] Implemented the `bump-version` skill and automated versioning tool for cross-component version synchronization.

### Changed
- [infra] Updated `package.json` files and component versions to follow the `0.5.x` semantic versioning scheme.

## [0.5.0] - 2026-03-26

### Added

- [frontend] "View Report" buttons added to the `PerformanceAnalysisDashboard` table to improve E2E test stability and user navigation.
- [backend] Google OAuth 2.0 integration: `users` table fields, `AuthService` logic, and API endpoints for authorization, callback, and token exchange.
- [frontend] Google Sign-In support: brand-compliant button, OAuth error handling, and session callback processing.
- [backend] Playbook, Tagging, and Psychological Note models with full CRUD API support.
- [backend] Time-series aggregation endpoints for P&L (daily/monthly), asset classes, symbols, and return distribution.
- [frontend] Initial dashboard visualization: metrics cards, equity curve, and drawdown charts using Recharts.
- [frontend] Advanced trade management: paginated trade list and broker import (IBKR/Schwab) UI.
- [infra] Iterative CI recovery skill (`ci-green-loop`) for automated triage and fix of GitHub Actions failures.

### Fixed

- [frontend] Performance Reports E2E tests (`reports.spec.ts`) now correctly locate and interact with the "View Report" buttons.

## [0.4.0] - 2026-03-15

### Added

- [backend] IBKR Activity Statement CSV parser and Charles Schwab trade history parser.
- [backend] Multi-part file upload endpoint for broker imports with ownership validation.

## [0.3.0] - 2026-03-01

### Added

- [backend] Performance metrics engine: win rate, profit factor, expectancy, Sharpe ratio, and max drawdown.
- [backend] Equity curve and drawdown curve time-series generation.

## [0.2.0] - 2026-02-15

### Added

- [backend] Multi-user support with User and Account models.
- [backend] JWT-based authentication with refresh token rotation and revocation.
- [backend] Account CRUD with strict user-level data isolation.

## [0.1.0] - 2026-02-01

### Added

- [backend] Initial data model and REST API for Trade management.
- [backend] TimescaleDB integration with hypertable partitioning for trades.
- [infra] Dockerized development stack and GitHub Actions CI/CD pipelines.

[0.15.0]: https://github.com/scheffold/OpenTradeJournal/compare/v0.14.0...v0.15.0
[0.14.0]: https://github.com/scheffold/OpenTradeJournal/compare/v0.13.0...v0.14.0
[0.5.1]: https://github.com/scheffold/OpenTradeJournal/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/scheffold/OpenTradeJournal/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/scheffold/OpenTradeJournal/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/scheffold/OpenTradeJournal/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/scheffold/OpenTradeJournal/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/scheffold/OpenTradeJournal/releases/tag/v0.1.0
[unreleased]: https://github.com/scheffold/OpenTradeJournal/compare/v0.15.0...HEAD
[0.7.0]: https://github.com/scheffold/OpenTradeJournal/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/scheffold/OpenTradeJournal/compare/v0.5.1...v0.6.0
