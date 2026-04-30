> **Execution order: Spec 1 of 3**
> Depends on: nothing — implement this first.
> See `openspec/changes/PORTFOLIO-EXECUTION-ORDER.md` for the full chain.

---

## Why

The current data model has no concept of a home currency per logical grouping of
accounts and no named boundary for grouping multiple accounts together.
Introducing a **Portfolio** entity as the top-level owner of accounts enables
portfolio-level currency configuration, makes future multi-currency aggregation
tractable without full trade history re-computation, and gives users a named,
colour-coded workspace per logical group of accounts.

## What Changes

- **NEW** `Portfolio` model and `portfolios` table — owned by a user; carries
  `name`, `base_currency`, and `color_hex`.
- **BREAKING** `Account.portfolio_id` (non-nullable FK) — every account must
  belong to exactly one portfolio.
- **NEW** full CRUD API for portfolios: `GET/POST /portfolios`,
  `GET/PATCH/DELETE /portfolios/{portfolio_id}`.
- **BREAKING** All trade/metrics/timeseries endpoints gain a mandatory
  `portfolio_id` scope: cross-portfolio access is rejected server-side.
- **NEW** Alembic migration that generates a default portfolio per existing
  user and links all existing accounts (and their trades) to it.
- **MODIFIED** metrics and timeseries aggregations respect
  `portfolio.base_currency` as the denominator for all PnL calculations.

## Capabilities

### New Capabilities

- `portfolio-management`: CRUD operations for the Portfolio entity; enforces
  ownership, name uniqueness per user, and immutability of `base_currency` once
  trades exist.
- `portfolio-api-isolation`: Server-side enforcement that every trade, metrics,
  timeseries, cash-transaction, and import request is scoped to a single
  portfolio; cross-portfolio requests are rejected with HTTP 400/403.

### Modified Capabilities

- `account-management`: Accounts gain a mandatory `portfolio_id` foreign key;
  account creation requires a valid portfolio_id owned by the current user.
- `trade-import`: Broker import endpoints receive an optional
  `portfolio_id` param; when omitted, default portfolio is used. Currency
  mismatch between imported trade currency and portfolio `base_currency` is
  flagged as a warning (not blocked).

## Impact

- **Database**: New `portfolios` table; `portfolio_id` column added to
  `accounts`; Alembic migration with data backfill.
- **Backend**: New `Portfolio` ORM model, Pydantic schemas, repository,
  service, and router; changes to `AccountRepository`, `TradeRepository`,
  `MetricsService`, `TimeseriesService`, and all import services to enforce
  portfolio scope.
- **Auth/RLS**: Portfolio-level ownership checks added to all scoped
  repositories; existing Row-Level Security policy extended.
- **Frontend**: `portfolio_id` becomes a required session-context value stored
  in React state / URL segment; all API calls updated via regenerated
  OpenAPI client. (Frontend work is out of scope for this spec — Spec 1 is
  backend only.)
- **Tests**: New portfolio unit tests; existing fixtures updated to create a
  default portfolio; integration tests verify isolation.
