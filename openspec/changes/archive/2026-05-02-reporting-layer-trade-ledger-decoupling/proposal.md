## Why

The current architecture conflates two fundamentally different concerns: *operational data management* (the Trade Ledger) and *analytical computation* (performance reporting). The existing `/metrics` endpoint computes aggregates on-demand from raw trade records, accepts sparse query parameters, and returns undifferentiated metric bundles — this works for simple use cases but breaks down as portfolios grow and filter combinations become complex.

Three pressures force a structural change now:

1. **Scale pressure.** A portfolio with 3,000+ trades and a filter combining playbook IDs, tags, direction, and a 2-year date range requires a full table scan with multi-join aggregation per request. No frontend pagination can hide this cost.

2. **Correlation requirement.** Spec 5 (Daily Check-in System) introduces `DailyCheckin` records keyed by `user_id + date`. Meaningful reporting requires joining trades to check-ins on `closed_at::date = DailyCheckin.date` to surface patterns like "win rate when market phase = TRENDING vs RANGING". This cross-entity query cannot be served by the current metrics endpoint without polluting it with checkin awareness.

3. **Statefulness requirement.** Users need to save dashboard configurations (filter sets) and reload them without re-specifying every parameter. The current stateless query-parameter approach provides no persistence primitive.

Critically, the aggregation responsibility must remain entirely server-side. Any design that returns raw or partially-filtered trade records to the frontend for client-side metric computation is explicitly rejected: it transfers unbounded data volumes across the network, violates the platform's API-first principle, and makes correlation with check-in data impossible without duplicating query logic in the frontend.

## What Changes

- New `SavedDashboardView` entity: persists user-defined dashboard filter configurations, scoped to a portfolio. Replaces (or extends) the existing `saved_trade_filters` functionality with dashboard-specific semantics.
- New Analytics Engine (`/analytics/` endpoints): dedicated routes that accept a `filter_config` JSONB or a `view_id` reference, execute all aggregation server-side, and return only computed metrics — never raw trade rows.
- New Attribution API (`/analytics/correlations/` endpoints): cross-entity endpoints that join `Trade` + `DailyCheckin` on date, grouping metrics by `market_phase`, allowing heatmap-ready server-side aggregation.
- Trade Ledger API hardening: existing `/trades` endpoints are explicitly scoped to raw data operations (CRUD, import, playbook/tag assignment). Aggregation logic is removed from the ledger layer and must not re-enter it.
- Database performance strategy: analytical query performance is ensured through correct composite indexes on all relevant filter and join columns. Materialized views are the designated escalation path if specific dashboard queries prove slow at scale — no external caching infrastructure is introduced.

## Capabilities

### New Capabilities

- `saved-dashboard-views`: Create, read, update, and delete named dashboard configurations. Each view is bound to a `portfolio_id` and stores a `filter_config` JSONB (date range, playbook IDs, tag IDs, direction, account IDs). Views can be materialized on demand or used as named aliases for analytics queries.
- `analytics-engine`: Dedicated `/analytics/` endpoints that consume a `filter_config` (inline or via `view_id`) and return fully computed metrics: win rate, profit factor, expectancy, Sharpe ratio, equity curve, drawdown curve. All computation is server-side.
- `attribution-api`: Cross-entity correlation endpoints. Primary endpoint: group trade metrics by `DailyCheckin.market_phase` for a given date range and portfolio. Returns heatmap-ready aggregates (e.g., win rate per market phase, avg PnL per phase). Requires `DailyCheckin` records to exist (Spec 5); gracefully returns empty buckets if none are present.
- `analytics-performance`: Composite database indexes on all filter and join columns used by analytics queries. Materialized views as a defined escalation path for queries that prove slow at scale. No external caching dependency.

### Modified Capabilities

- `trade-ledger`: The `GET /trades` list endpoint is clarified as a raw data endpoint only. No aggregation logic may be added. Filter parameters remain (for pagination/display), but metrics are not computed inline.
- `metrics`: Existing `/metrics/summary`, `/metrics/equity-curve`, and `/metrics/drawdown` endpoints are deprecated in favour of the new analytics engine. A migration path is documented; endpoints remain functional until a major version bump.

## Impact

- **Backend**: New ORM model (`SavedDashboardView`), new repository (`analytics_repository.py`, `attribution_repository.py`), new services (`analytics_service.py`, `attribution_service.py`), new API routes under `/api/v1/portfolios/{portfolio_id}/analytics/` and `/api/v1/portfolios/{portfolio_id}/views/`.
- **Database**: One new table (`saved_dashboard_views`) + Alembic migration. Analytics queries use existing `trades`, `trade_tags`, `playbook`, `daily_checkins` tables via joins — no schema changes to those tables. New composite indexes are added to `trades` and `daily_checkins` to support filter and join patterns.
- **Caching**: No external caching dependency. The database is the single source of truth. Performance is managed at the query and index level. PostgreSQL Materialized Views are available as a future escalation path.
- **Frontend**: Out of scope for this change. Existing `/metrics` endpoints remain available during the transition period.
- **Spec 5 dependency**: `attribution-api` capability depends on `DailyCheckin` model and `daily_checkins` table being present. This change's attribution routes must fail gracefully (HTTP 503 or empty results) if Spec 5 is not yet deployed.
