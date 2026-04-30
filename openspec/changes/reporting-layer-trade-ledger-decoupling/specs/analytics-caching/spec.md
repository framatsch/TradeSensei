## ADDED Requirements

### Requirement: Composite indexes on analytics filter columns
The database migration for this change SHALL add composite indexes on all columns used as filters or join keys in analytics queries.

#### Scenario: Analytics query uses portfolio-scoped date filter
- **WHEN** an analytics summary is requested with a date range for a portfolio
- **THEN** the query SHALL use the `(user_id, portfolio_id, closed_at)` index on `trades` — verified via `EXPLAIN ANALYZE` during development showing no sequential scan on `trades`

#### Scenario: Playbook-filtered analytics query
- **WHEN** a filter_config includes `playbook_ids`
- **THEN** the query SHALL use the `(user_id, portfolio_id, playbook_id, closed_at)` index on `trades`

#### Scenario: Attribution join uses index on daily_checkins
- **WHEN** the attribution endpoint joins `trades.closed_at::date` to `daily_checkins.date`
- **THEN** the join SHALL use the existing unique index on `(user_id, date)` in `daily_checkins` — no sequential scan on that table

### Requirement: Analytics repository uses set-based SQL, not per-row Python loops
All aggregation in the analytics repository layer SHALL be expressed as a single SQL statement (or minimal number of queries) using JOINs, GROUP BY, and aggregate functions. Fetching all rows into Python and computing metrics in a loop is not permitted for cross-entity queries.

#### Scenario: Market-phase correlation computed in SQL
- **WHEN** the attribution endpoint is called
- **THEN** grouping by `market_phase` and computation of `count`, `win_rate`, `avg_pnl`, `total_pnl` per bucket SHALL occur in a single SQL GROUP BY query — individual trade rows are NOT returned from the repository for Python-level grouping

#### Scenario: Analytics summary aggregation
- **WHEN** the analytics summary is requested
- **THEN** scalar aggregates (gross_profit, gross_loss, win count, loss count, streaks) SHALL be computed in SQL where possible, reducing the data transferred from database to application layer

### Requirement: Materialized views are the defined escalation path for slow queries
If a specific analytics query is identified as consistently slow on realistic datasets (measured, not assumed), PostgreSQL Materialized Views MAY be introduced as a pre-aggregation mechanism. This is NOT implemented in this iteration.

#### Scenario: Slow query identified post-deployment
- **WHEN** a specific `SavedDashboardView` query is measured to exceed an acceptable latency threshold
- **THEN** the engineering decision to introduce a materialized view for that pattern is evaluated, using the existing database infrastructure — no external caching layer is introduced

#### Scenario: No speculative pre-aggregation
- **WHEN** a new analytics endpoint is implemented
- **THEN** it SHALL NOT speculatively create materialized views or pre-aggregation tables before a performance problem is observed and measured

### Requirement: Redis cache invalidation includes DailyCheckin and MarketPhaseDefinition writes
When Redis caching is active, any write that affects the data used by attribution queries SHALL invalidate the relevant cache keys. Check-in data is user-scoped (not portfolio-scoped), so invalidation must cover all portfolios of the affected user.

#### Scenario: DailyCheckin created, updated, or deleted
- **WHEN** a `DailyCheckin` record is written or deleted for a user
- **THEN** all cached attribution keys for that user SHALL be invalidated — implementation SHALL invalidate across all of the user's portfolios (pattern: `analytics:*:{user_id}:*` or iterate portfolio IDs)

#### Scenario: MarketPhaseDefinition updated or deactivated
- **WHEN** a user updates a `MarketPhaseDefinition` (label, color, or `is_active`)
- **THEN** all cached attribution keys for that user SHALL be invalidated, since label changes affect response display and deactivation affects future check-in validation
