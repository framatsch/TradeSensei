## Context

The platform currently has one analytics path: `GET /portfolios/{portfolio_id}/metrics/summary`, which calls `MetricsService.get_summary()`, which calls `MetricsRepository` to fetch all closed trades and then applies pure utility functions (`compute_trade_metrics`, `compute_equity_curve`, `compute_drawdown_curve`). This path is stateless, computes everything in Python, and has no cross-entity awareness.

Spec 5 (Daily Check-in System) is being implemented in parallel. It introduces `DailyCheckin` rows keyed by `(user_id, date)` with a `market_phase` field. The reporting layer must be able to join trade outcomes to check-in context — this is the primary analytical differentiator of the platform.

The existing `SavedTradeFilter` model stores filter definitions but is not bound to a portfolio and has no concept of a "dashboard configuration." It was designed for trade list filtering, not as a unit of analytical configuration.

The `FxRate` table stores daily ECB reference rates. There is currently **no mechanism for currency-normalizing historical trade PnL** when a saved view spans trades executed in multiple currencies. This is a critical gap: a view covering trades from 2022–2024 where the account's base currency changed, or where trades were in multiple currencies, will aggregate PnL values in incompatible units unless FX normalization is applied at query time. This design must define an explicit policy.

## Goals / Non-Goals

**Goals:**
- Define the `SavedDashboardView` data model with explicit `portfolio_id` binding and a validated `filter_config` schema
- Specify the Analytics Engine API contract: input shape, output shape, aggregation responsibilities
- Specify the Attribution API contract: the join strategy between `trades` and `daily_checkins`, grouping semantics, and empty-bucket handling
- Define the database performance strategy: indexes and materialized views as the primary tools for query performance
- Define the FX normalization policy for cross-currency analytics
- Harden the Trade Ledger API contract: document what the `/trades` endpoints are and are not responsible for

**Non-Goals:**
- Frontend implementation of dashboard views
- Real-time streaming analytics
- Multi-portfolio aggregation (views are single-portfolio)
- Admin-level cross-user analytics
- Replacing existing `/metrics` endpoints before a deprecation period (they remain functional)
- Automatic backfill of historical FX rates (the `fx_rate_service` handles on-demand fetching)

## Decisions

### D1 — `SavedDashboardView` is a new model, not an extension of `SavedTradeFilter`

**Decision**: Create a new `saved_dashboard_views` table. Do not repurpose `SavedTradeFilter`.

**Rationale**: `SavedTradeFilter` is scoped to `user_id` without portfolio binding, uses a generic `definition` JSONB with no enforced schema, and has a `scope` enum (`SYSTEM` / `USER`) that conflates admin and user filters. Dashboard views require mandatory `portfolio_id` binding, a typed `filter_config` schema, and different ownership semantics. Merging the two would require breaking changes to the existing model and would produce an overloaded, confusing entity.

**Trade-off**: Two similar-looking tables exist for a period. Resolution: deprecate `SavedTradeFilter` in a follow-up iteration and migrate usages to `SavedDashboardView`. Document this explicitly.

**`filter_config` schema** (JSONB with server-side validation):
```json
{
  "date_from": "ISO-8601 or null",
  "date_to": "ISO-8601 or null",
  "playbook_ids": ["uuid", ...],
  "tag_ids": ["uuid", ...],
  "direction": "LONG | SHORT | null",
  "account_ids": ["uuid", ...],
  "currency_mode": "NATIVE | NORMALIZED",
  "normalize_to": "ISO-4217 currency code (required when currency_mode = NORMALIZED)"
}
```

The `currency_mode` and `normalize_to` fields address the FX problem directly — see D5.

### D2 — Analytics Engine: server-side aggregation, filter_config as the unit of query specification

**Decision**: The `/analytics/summary` endpoint accepts either an inline `filter_config` object (for ad-hoc queries) or a `view_id` UUID (to load a saved view). It returns only computed metrics — no trade rows, no cursor tokens.

**Rationale**: Returning raw rows to the frontend for aggregation is explicitly rejected. It transfers unbounded data (a 3-year portfolio could have thousands of trades), duplicates the aggregation logic client-side, and makes cross-entity correlation impossible without a second API call.

**Response contract** (`AnalyticsSummary`):
```
win_rate: Decimal
profit_factor: Decimal
expectancy: Decimal
sharpe_ratio: Decimal | null  (null when fewer than 2 trades)
total_trades: int
winning_trades: int
losing_trades: int
gross_profit: Decimal
gross_loss: Decimal
avg_win: Decimal
avg_loss: Decimal
max_consecutive_wins: int
max_consecutive_losses: int
avg_trade_duration_hours: Decimal | null
equity_curve: list[EquityCurvePoint]  (capped at EQUITY_CURVE_MAX_POINTS)
drawdown_curve: list[DrawdownPoint]
max_drawdown: Decimal
max_drawdown_abs: Decimal
currency: str  (ISO-4217 — the currency all monetary values are expressed in)
```

**`currency` field is mandatory on the response.** The frontend must display the currency symbol alongside all monetary values. Omitting it would be a silent correctness bug.

### D3 — Attribution API: join strategy and grouping

**Decision**: The primary attribution endpoint is `GET /analytics/correlations/market-phase`. It joins `trades` to `daily_checkins` on `trades.closed_at::date = daily_checkins.date AND daily_checkins.user_id = :user_id`. Grouping is by `daily_checkins.market_phase`. Bucket keys are the distinct `market_phase` name strings actually present in the matched check-in records — there is no fixed enum. The service layer resolves `label` and `color_hex` for each bucket by joining to `MarketPhaseDefinition`. If a historical check-in references a phase name with no matching `MarketPhaseDefinition` (e.g. a phase the user deleted), the raw name is used as the `label` and `color_hex` is `null` — the bucket is still returned.

**Join semantics:**
- **Inner join** (strict): only trades that have a matching check-in on their close date are included. Trades with no check-in are excluded from the grouped results. The response includes an `unmatched_trade_count` field so the frontend can warn the user.
- **Rationale for inner join over left join**: a left join would silently include trades in a `null` market-phase bucket, which is misleading in a heatmap visualization. Explicit `unmatched_trade_count` is more honest.

**Response contract** (`MarketPhaseCorrelation`):
```
market_phase: str  (the name string from DailyCheckin.market_phase — user-defined, no fixed enum)
label: str         (resolved from MarketPhaseDefinition.label; falls back to market_phase if no definition found)
color_hex: str | null  (resolved from MarketPhaseDefinition.color_hex; null if no definition found)
trade_count: int
win_rate: Decimal
profit_factor: Decimal
avg_pnl: Decimal
total_pnl: Decimal
currency: str
```

**Empty-bucket handling**: if no `DailyCheckin` records exist for the date range, the endpoint returns an empty `buckets` array with `unmatched_trade_count = total_trades_in_range` and `phase_unset_trade_count = 0`. If check-ins exist but all have `market_phase = null`, then `unmatched_trade_count = 0`, `phase_unset_trade_count = total_trades_in_range`, and `buckets = []`. HTTP 200 in both cases, not 404.

**Spec 5 dependency**: the `DailyCheckin` model must exist. If the `daily_checkins` table does not exist (Spec 5 not deployed), the endpoint returns HTTP 503 with `{"detail": "daily_checkins table not available — deploy Spec 5 first"}`. This is detected at startup via a lightweight table existence check.

### D4 — Performance strategy: indexes first, materialized views as escalation

**Decision**: No external caching layer (Redis or equivalent) is introduced. Query performance is managed entirely within the existing PostgreSQL/TimescaleDB infrastructure. The approach is:

1. **Correct composite indexes at migration time** (mandatory, done in this iteration):
   - `trades`: `(user_id, portfolio_id, closed_at)` — primary analytics filter
   - `trades`: `(user_id, portfolio_id, playbook_id, closed_at)` — playbook-filtered queries
   - `trade_tags`: `(trade_id, tag_id)` — join for tag filtering
   - `daily_checkins`: `(user_id, date)` — attribution join (already a unique constraint from Spec 5; verify index exists)
   - `saved_dashboard_views`: `(user_id, portfolio_id)` — view list lookup

2. **Query design constraints** (enforced in analytics_repository.py):
   - Analytics queries must use a single SQL statement with JOINs and GROUP BY — no Python-level loops over per-row results
   - The repository layer must use `EXPLAIN ANALYZE` output during development to verify index usage on representative datasets

3. **Materialized views as a defined escalation path** (deferred, not in scope for this iteration):
   - If a specific `SavedDashboardView` is identified as slow (e.g., a 3-year all-trades query with complex joins), PostgreSQL Materialized Views can pre-aggregate results on the database
   - Materialized view refresh can be triggered after trade write operations using a PostgreSQL function or a background job
   - This decision is deferred until a concrete query performance problem is observed and measured — it is not implemented speculatively

**Rationale**: Trading portfolios of typical individual users (100–5,000 trades) are well within the capacity of a properly indexed relational database to aggregate in real time. Introducing Redis as an additional infrastructure component increases deployment complexity (new service, connection management, serialization, invalidation logic, operational monitoring) without a demonstrated need. The trade-off favours simplicity and correctness over premature optimization.

**What this decision does NOT address**: concurrent high-frequency requests from many users hitting the same complex query simultaneously. If the platform ever reaches that scale, the materialized view path (or read replicas) provides the escalation route without requiring a cache layer to be retrofitted.

### D5 — FX normalization policy for cross-currency analytics

**Critical gap resolved**: The `trade.pnl` field is stored in the **account's base currency** — the import parsers (IBKR, Schwab) normalize PnL to the account base currency at import time. Trades denominated in a different currency than the account base currency are **rejected at import time with an explicit error** — they are never persisted. This means that within a single account all `pnl` values are always in one currency (the account's base currency).

**Implication**: The cross-currency problem is scoped to the portfolio level, not the trade level. A portfolio may contain multiple accounts each with a different base currency. Within each account, PnL is already currency-consistent.

**Decision**: The `filter_config` includes an explicit `currency_mode` field:

- `NATIVE` (default): when all filtered trades are in the same currency, metrics are computed and the `currency` field is set to that currency. When the filter spans multiple account currencies, the response returns **per-currency sub-summaries** in a `currency_summaries` list alongside an overall `warnings` array indicating mixed currencies. HTTP 422 is NOT returned — the user receives valid data with a transparent warning.
- `NORMALIZED`: all monetary PnL values are converted to `normalize_to` currency using the ECB rate on `trade.closed_at::date`. The `FxRate` table is queried per trade date. If an FX rate is missing for a given date (weekend, holiday, data gap), the service falls back to the nearest available rate within ±3 calendar days. If no rate is found within that window, the trade is excluded from aggregation and its ID is listed in a `fx_rate_missing_trade_ids` response field.

**Explicit decisions made**:
1. `trade.pnl` is always in the account base currency — confirmed. No per-trade FX lookup needed within an account.
2. `NATIVE` mode with mixed account currencies returns per-currency sub-summaries + warning, not HTTP 422.
3. `fx_rate_date` is included in normalized sub-entries to make the point-in-time semantic explicit to the frontend.

**Recommendation**: The `AnalyticsSummary` response shape must be updated to carry either a single `currency` + flat metrics (single-currency case) or a `currency_summaries` list (multi-currency NATIVE case). See specs/analytics-engine/spec.md for the updated contract.

### D6 — Trade Ledger API hardening

**Decision**: The `/trades` endpoints retain all existing functionality (CRUD, pagination, filtering, playbook/tag assignment, merge, partial close). No aggregation endpoints are added to the trades router. Any PR adding metric computation to a trades route handler will be rejected in code review.

**Rationale**: The ledger is the system of record. Its job is accurate representation of raw trade data. Mixing aggregation concerns into it creates coupling that defeats the decoupling this spec is designed to achieve.

**Explicit contract for `/trades` list endpoint**:
- Returns paginated `TradeRead` objects
- Accepts filter parameters for display purposes (date range, playbook, tags, direction)
- Does NOT compute win rates, equity curves, or any metric
- Does NOT join to `DailyCheckin` data

### D7 — Deprecation path for existing `/metrics` endpoints

**Decision**: Existing `/metrics/summary`, `/metrics/equity-curve`, and `/metrics/drawdown` endpoints are marked `deprecated=True` in the FastAPI route decorator. They continue to function. A response header `Deprecation: true` and `Sunset: <date>` (set to 6 months from implementation date) is added. They are removed in the next major API version.

**Rationale**: Breaking existing integrations (including the current frontend) without a migration path violates the platform's API stability contract.

## Risks / Trade-offs

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Analytics query slow for very large date ranges without proper indexes | Medium | Mandatory composite indexes in migration; `EXPLAIN ANALYZE` review during development |
| Missing index causes full table scan on attribution join | Medium | `daily_checkins (user_id, date)` index mandatory; verify via query plan |
| Attribution endpoint returns misleading results if check-in coverage is low | Medium | `unmatched_trade_count` in response; frontend must surface this to users |
| `filter_config` JSONB schema drift over time (e.g., new filter fields) | Medium | Validate `filter_config` in the service layer against a Pydantic model (`DashboardFilterConfig`); no `_schema_version` field needed |
| Inner join in attribution excludes many trades (low check-in discipline) | Medium | `unmatched_trade_count` makes exclusion explicit; provide a `JOIN_MODE` query param (`INNER` / `LEFT`) in a future iteration if user feedback demands it |
| `SavedTradeFilter` and `SavedDashboardView` coexist indefinitely | Low | Deprecation plan in D1; track in a follow-up issue; no migration of existing records |
| FX rate gaps (weekends, data outages) silently distort normalized metrics | Medium | List `fx_rate_missing_trade_ids` in response; do not silently aggregate over missing rates |

## Open Questions

**OQ-1 — RESOLVED**: `trade.pnl` is stored in the account's base currency. Import parsers reject trades denominated in a different currency than the account base currency with an explicit error. No per-trade FX lookup is needed within an account.

**OQ-2 — RESOLVED**: Multi-currency NATIVE mode returns HTTP 200 with a `currency_summaries` list (one entry per currency) and a `warnings` array containing a `"mixed_currencies"` entry. Non-monetary aggregate metrics are still computed across all trades; monetary fields at the top level are `null` in the multi-currency case. The frontend is responsible for surfacing the warning and offering a switch to `NORMALIZED` mode.

**OQ-3 — RESOLVED**: No migration of existing `SavedTradeFilter` records to `SavedDashboardView`. The two models coexist; `SavedTradeFilter` is deprecated in D1 and will be removed in a future major version. Users recreate their filters in the new view system.

**OQ-4 — Analytics endpoint pagination**: The `equity_curve` list is capped at `EQUITY_CURVE_MAX_POINTS` (currently 1,000). For very large portfolios, this truncation loses detail. Should the analytics engine support a `resolution` parameter (e.g., `daily` / `weekly` / `monthly` bucketing) instead of a hard cap? Recommended: yes, but deferred to a follow-up iteration — hard cap is acceptable for now.

**OQ-5 — Attribution endpoint for custom check-in fields**: The market-phase correlation endpoint is defined. Should the attribution API support grouping by *custom* `DailyCheckin` fields (e.g., "mood-level ≥ 7")? This is architecturally possible but out of scope for this iteration. Flag as a planned extension point.
