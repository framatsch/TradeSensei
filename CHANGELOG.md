# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[0.5.0]: https://github.com/scheffold/OpenTradeJournal/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/scheffold/OpenTradeJournal/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/scheffold/OpenTradeJournal/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/scheffold/OpenTradeJournal/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/scheffold/OpenTradeJournal/releases/tag/v0.1.0
[unreleased]: https://github.com/scheffold/OpenTradeJournal/compare/v0.5.0...HEAD
