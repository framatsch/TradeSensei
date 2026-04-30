## ADDED Requirements

### Requirement: Group trade metrics by market phase
The attribution API SHALL join trade outcomes to `DailyCheckin` records on close date and return metrics grouped by `market_phase`. Bucket keys are the distinct `market_phase` name values actually present in the matched check-in records — there is no fixed enum. The display `label` and `color_hex` for each bucket SHALL be resolved by joining to the user's `MarketPhaseDefinition` records. If a historical check-in references a phase name that no longer has an active (or any) `MarketPhaseDefinition`, the raw `name` string is used as the `label` and `color_hex` is `null`.

#### Scenario: Successful correlation request with default phases
- **WHEN** a user sends `GET /api/v1/portfolios/{portfolio_id}/analytics/correlations/market-phase` and their check-ins use only the four default phases
- **THEN** the system returns HTTP 200 with up to four `MarketPhaseCorrelation` buckets — one per distinct phase name observed in matched check-ins — with `label` and `color_hex` resolved from `MarketPhaseDefinition`

#### Scenario: Successful correlation request with custom phases
- **WHEN** a user has created custom `MarketPhaseDefinition` records (e.g. `trending`, `ranging`) and their check-ins use those names
- **THEN** the system returns HTTP 200 with buckets keyed by those custom names, with `label` and `color_hex` resolved from the user's own `MarketPhaseDefinition` records

#### Scenario: Historical check-in references a deactivated or deleted phase
- **WHEN** a check-in's `market_phase` value has no matching `MarketPhaseDefinition` for the user (phase was deleted or the name is unknown)
- **THEN** the bucket is still returned with `market_phase` set to the raw name, `label` set to the raw name, and `color_hex` set to `null`

#### Scenario: All aggregation is server-side
- **WHEN** the correlation endpoint is called
- **THEN** all grouping, counting, win-rate computation, and PnL aggregation SHALL occur in the database query or service layer — the response SHALL NOT include individual trade records

#### Scenario: No check-in records exist for the date range
- **WHEN** the user has no `DailyCheckin` records for the requested period
- **THEN** the system returns HTTP 200 with `buckets = []` and `unmatched_trade_count` set to the total number of closed trades in the period

#### Scenario: Some trades have no matching check-in
- **WHEN** some trades' close dates have no matching `DailyCheckin`
- **THEN** those trades are excluded from all `MarketPhaseCorrelation` buckets and their count is reported in `unmatched_trade_count`

#### Scenario: Inner-join semantics — trades without check-ins are excluded, not silently bucketed
- **WHEN** a trade has no check-in on its close date
- **THEN** it SHALL NOT appear in any `market_phase` bucket, even as `null` or "UNKNOWN"

### Requirement: Attribution response includes unmatched trade count and phase-unset trade count
The system SHALL always report two exclusion counts:
- `unmatched_trade_count`: trades whose close date has **no** `DailyCheckin` record at all
- `phase_unset_trade_count`: trades whose close date has a `DailyCheckin` but with `market_phase = null` (check-in exists but phase was not yet filled in)

Both counts are separate so the frontend can give the user actionable guidance: "X trades have no check-in" vs. "Y trades have a check-in but no phase set yet — update them to include them in the analysis."

#### Scenario: Response shape with partial match
- **WHEN** 10 trades are in the date range, 3 have no check-in, and 2 have a check-in with `market_phase = null`
- **THEN** the response includes `unmatched_trade_count = 3`, `phase_unset_trade_count = 2`, and the buckets aggregate the remaining 5 trades

#### Scenario: All trades matched with phase
- **WHEN** all trades in the date range have a check-in with a non-null `market_phase`
- **THEN** `unmatched_trade_count = 0` and `phase_unset_trade_count = 0`

### Requirement: Attribution endpoint handles missing DailyCheckin table gracefully
If Spec 5 (Daily Check-in System) has not been deployed, the attribution endpoint SHALL not crash or return misleading data.

#### Scenario: daily_checkins table does not exist
- **WHEN** the attribution endpoint is called and the `daily_checkins` table is absent
- **THEN** the system returns HTTP 503 with `{"detail": "daily_checkins table not available — deploy Spec 5 first"}`

#### Scenario: daily_checkins table exists but is empty
- **WHEN** the table exists but has no rows for the user
- **THEN** the system returns HTTP 200 with empty buckets and `unmatched_trade_count = total_trades_in_range`

### Requirement: Attribution endpoint respects portfolio scope
All trade and check-in data used in correlation SHALL be scoped to the authenticated user. Cross-user data leakage is not permitted.

#### Scenario: User A cannot see User B's correlation data
- **WHEN** User A requests correlations for their portfolio
- **THEN** only User A's trades and User A's check-in records are used — User B's check-ins are never joined

### Requirement: Attribution endpoint supports filter_config or view_id
The correlation endpoint SHALL accept the same filter surface as the analytics engine.

#### Scenario: filter_config scoping
- **WHEN** a `filter_config` with `playbook_ids` and a date range is provided
- **THEN** only trades matching those filters are included in the correlation buckets
