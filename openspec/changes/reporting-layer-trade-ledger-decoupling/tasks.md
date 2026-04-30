## 1. Database Model & Migration

- [ ] 1.1 Create `SavedDashboardView` SQLAlchemy ORM model with columns: `id`, `user_id` (FK → users), `portfolio_id` (FK → portfolios), `name` (VARCHAR), `filter_config` (JSONB), `created_at`, `updated_at`
- [ ] 1.2 Add index on `(portfolio_id, user_id)` to `SavedDashboardView`
- [ ] 1.3 Add composite index `(user_id, portfolio_id, closed_at)` to `trades` (for analytics filter queries)
- [ ] 1.4 Add composite index `(user_id, portfolio_id, playbook_id, closed_at)` to `trades` (for playbook-filtered analytics)
- [ ] 1.5 Generate Alembic migration: create `saved_dashboard_views` table and add indexes in tasks 1.3–1.4
- [ ] 1.6 Apply migration locally and verify table and indexes via `EXPLAIN ANALYZE` on a sample analytics query

## 2. Pydantic Schemas

- [ ] 2.1 Create `DashboardFilterConfig` Pydantic model: optional `date_from` (ISO-8601 date or null), optional `date_to`, optional `playbook_ids: list[UUID]`, optional `tag_ids: list[UUID]`, optional `direction: "LONG" | "SHORT" | null`, optional `account_ids: list[UUID]`, `currency_mode: "NATIVE" | "NORMALIZED"` (default `"NATIVE"`), optional `normalize_to` (ISO-4217 string, required when `currency_mode="NORMALIZED"`). Add `_schema_version: str = "1"` for future drift detection. Add validator: `date_from` must not be later than `date_to` when both are provided; `normalize_to` is required when `currency_mode="NORMALIZED"`.
- [ ] 2.2 Create `SavedDashboardViewCreate` schema: `name` (str), `filter_config` (DashboardFilterConfig)
- [ ] 2.3 Create `SavedDashboardViewUpdate` schema: optional `name`, optional `filter_config`
- [ ] 2.4 Create `SavedDashboardViewRead` schema: all fields including `id`, `created_at`, `updated_at`
- [ ] 2.5 Create `AnalyticsSummary` Pydantic model per design.md D2 contract: all scalar metrics, `equity_curve: list[EquityCurvePoint]`, `drawdown_curve: list[DrawdownPoint]`, `currency: str | null`, `multi_currency_warning: bool` (default False), `currencies: list[PerCurrencySummary] | None`, `fx_rate_missing_trade_ids: list[UUID] | None`
- [ ] 2.6 Create `PerCurrencySummary` schema: subset of `AnalyticsSummary` monetary fields + `currency: str`
- [ ] 2.7 Create `EquityCurvePoint` schema: `date: date`, `equity: Decimal`, `currency: str`
- [ ] 2.8 Create `DrawdownPoint` schema: `date: date`, `drawdown_pct: Decimal`, `drawdown_abs: Decimal`
- [ ] 2.9 Create `MarketPhaseCorrelation` schema: `market_phase: str` (the raw name string from `DailyCheckin.market_phase` — no fixed enum), `label: str` (resolved from `MarketPhaseDefinition.label`; falls back to `market_phase` if no definition exists), `color_hex: str | None` (resolved from `MarketPhaseDefinition.color_hex`; `null` if no definition exists), `trade_count: int`, `win_rate: Decimal`, `profit_factor: Decimal`, `avg_pnl: Decimal`, `total_pnl: Decimal`, `currency: str`
- [ ] 2.10 Create `AttributionResponse` schema: `buckets: list[MarketPhaseCorrelation]`, `unmatched_trade_count: int` (trades with no check-in on close date), `phase_unset_trade_count: int` (trades with check-in but `market_phase = null`), `currency: str | null`
- [ ] 2.11 Create `AnalyticsSummaryRequest` schema: one of `filter_config` (inline) or `view_id` (UUID) — implement as a discriminated union or separate fields with a root validator ensuring exactly one is provided

## 3. Repository Layer

- [ ] 3.1 Create `SavedDashboardViewRepository` with methods: `create`, `get_by_id`, `list_by_portfolio`, `update`, `delete`
- [ ] 3.2 Create `AnalyticsRepository` with method `compute_summary(portfolio_id, user_id, filter_config, session) -> RawAggregates`: executes a single SQL query using JOINs and GROUP BY — returns scalar aggregates (gross_profit, gross_loss, win/loss counts, streaks) and raw equity-curve data rows. No per-row Python loops.
- [ ] 3.3 Create `AttributionRepository` with method `compute_market_phase_correlation(portfolio_id, user_id, filter_config, session) -> list[PhaseAggregateRow]`: executes a single SQL JOIN between `trades` and `daily_checkins` on `closed_at::date = date AND daily_checkins.user_id = user_id`, GROUP BY `market_phase`, returns aggregate rows. Handles missing `daily_checkins` table gracefully (catch `ProgrammingError` / table existence check at startup).

## 4. Service Layer

- [ ] 4.1 Create `SavedDashboardViewService` with methods: `create_view`, `list_views`, `get_view`, `update_view` (invalidate cache on success), `delete_view` (invalidate cache on success). Enforce `portfolio_id` ownership (return 403 if portfolio belongs to different user).
- [ ] 4.2 Create `AnalyticsService` with method `get_summary(portfolio_id, user_id, request, session)`: resolves `view_id` → `filter_config` if needed; checks cache first; computes via `AnalyticsRepository`; applies FX normalization (D5) if `currency_mode="NORMALIZED"`; applies multi-currency warning logic if `currency_mode="NATIVE"` with mixed currencies; stores result in cache with TTL=300s.
- [ ] 4.3 Create `AttributionService` with method `get_market_phase_correlation(portfolio_id, user_id, filter_config, session)`: checks cache first (TTL=900s); calls `AttributionRepository`; joins `MarketPhaseDefinition` records to resolve `label` and `color_hex` for each bucket (fallback to raw `market_phase` name and `null` color if no definition found); returns `AttributionResponse`. Cache invalidation: on `DailyCheckin` and `MarketPhaseDefinition` writes.
- [ ] 4.4 Implement FX normalization logic in `AnalyticsService`: for each trade in `NORMALIZED` mode, look up `FxRate` for `closed_at::date`; fall back to nearest within ±3 calendar days (prefer rate on or before the trade date as tie-breaker); exclude trade and add to `fx_rate_missing_trade_ids` if no rate found within window.
- [ ] 4.5 Implement equity curve downsampling in `AnalyticsService`: cap at `EQUITY_CURVE_MAX_POINTS` (configurable, default 1000) using time-bucketing; do NOT return raw trade rows for client-side downsampling.

## 5. Caching Layer

- [ ] 5.1 Create `CacheService` with methods: `get(key) -> str | None`, `set(key, value, ttl)`, `invalidate_portfolio(portfolio_id, user_id)`, `invalidate_user(user_id)`. Redis backend when `REDIS_URL` is set; no-op pass-through otherwise (log WARNING at startup).
- [ ] 5.2 Cache key structure: `analytics:{portfolio_id}:{user_id}:{sha256(filter_config_json_canonical)}` — use canonical JSON serialization (sorted keys) to ensure identical configs produce the same hash.
- [ ] 5.3 Wire `invalidate_portfolio(portfolio_id, user_id)` into trade CRUD service (after each write) and `SavedDashboardViewService` (after update/delete).
- [ ] 5.4 Wire `invalidate_user(user_id)` into `DailyCheckinService` (after each write/delete) and `MarketPhaseDefinitionService` (after update).

## 6. API Routes

- [ ] 6.1 Create `/api/v1/portfolios/{portfolio_id}/views` router: `POST /` (create view), `GET /` (list views), `GET /{view_id}` (get single view), `PATCH /{view_id}` (update), `DELETE /{view_id}` (delete)
- [ ] 6.2 Create `/api/v1/portfolios/{portfolio_id}/analytics` router: `POST /summary` (inline filter_config or view_id in body), `GET /correlations/market-phase` (optional `from_date`, `to_date`, `view_id` query params)
- [ ] 6.3 Add deprecation markers to existing metrics endpoints in `app/api/v1/metrics.py`: set `deprecated=True` in route decorator; add response header `Deprecation: true` and `Sunset: <date 6 months from implementation>`
- [ ] 6.4 Register new routers in `app/api/v1/router.py`
- [ ] 6.5 Ensure all new routes require authentication (`Depends(get_current_user)`) and portfolio ownership check

## 7. Attribution Spec-5 Dependency Guard

- [ ] 7.1 At `AttributionRepository` startup (or on first call), check for `daily_checkins` table existence via a lightweight query. If absent, raise a custom `Spec5NotDeployedError`.
- [ ] 7.2 In `AttributionService`, catch `Spec5NotDeployedError` and return HTTP 503 with `{"detail": "daily_checkins table not available — deploy Spec 5 first"}`

## 8. Tests

- [ ] 8.1 Unit tests for `DashboardFilterConfig` validation: `date_from > date_to` → 422, `NORMALIZED` without `normalize_to` → 422, default `currency_mode = NATIVE`
- [ ] 8.2 Unit tests for FX normalization: rate found on exact date, rate found within ±3 days (prefer on-or-before), rate missing → trade excluded + ID in `fx_rate_missing_trade_ids`
- [ ] 8.3 Unit tests for multi-currency NATIVE mode: single currency → normal response, mixed currencies → `multi_currency_warning=true`, `currency=null`, per-currency sub-summaries present
- [ ] 8.4 Unit tests for equity curve downsampling: count ≤ MAX_POINTS passes through unchanged, count > MAX_POINTS is downsampled to ≤ MAX_POINTS
- [ ] 8.5 Integration tests for `SavedDashboardView` CRUD: create, list, get single, update triggers cache invalidation, delete triggers cache invalidation, foreign portfolio returns 403
- [ ] 8.6 Integration tests for analytics summary: inline filter_config, view_id alias, 0 trades → zeroed metrics + empty curves, 1 trade → sharpe_ratio null, multi-currency NATIVE → warning response
- [ ] 8.7 Integration tests for attribution: success with default phases → buckets include resolved `label` and `color_hex`; success with custom phases → custom phase name returned as bucket key; historical check-in with deleted/unknown phase → bucket returned with raw name as `label` and `color_hex=null`; check-in with `market_phase=null` → trade counted in `phase_unset_trade_count`, not `unmatched_trade_count`; empty check-ins → `buckets=[]` + `unmatched_trade_count`; partial match → correct counts; `daily_checkins` absent → 503
- [ ] 8.8 Integration tests for cache: hit returns stored result, trade write invalidates cache, DailyCheckin write invalidates attribution cache across all user portfolios
- [ ] 8.9 Integration test for deprecated metrics endpoints: still return 200 with correct data, response includes `Deprecation` and `Sunset` headers

## 9. OpenAPI Annotations

- [ ] 9.1 Add `summary`, `description`, `response_model`, `deprecated` to all new and modified route handlers
- [ ] 9.2 Add `Field(description=...)` to all new Pydantic schema fields
- [ ] 9.3 Regenerate frontend OpenAPI client (`openapi-sync` skill)
