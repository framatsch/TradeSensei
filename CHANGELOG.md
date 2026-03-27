# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[0.5.1]: https://github.com/scheffold/OpenTradeJournal/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/scheffold/OpenTradeJournal/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/scheffold/OpenTradeJournal/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/scheffold/OpenTradeJournal/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/scheffold/OpenTradeJournal/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/scheffold/OpenTradeJournal/releases/tag/v0.1.0
[unreleased]: https://github.com/scheffold/OpenTradeJournal/compare/v0.5.1...HEAD
