## ADDED Requirements

### Requirement: Attribution endpoint uses LEFT JOIN semantics for uncategorized trades
The attribution SHALL use a `LEFT JOIN` from the trade ledger to `DailyCheckin` records on close date. Trades without a matching check-in record SHALL NOT be excluded — instead they SHALL be aggregated into an explicit `uncategorized` bucket in the response. This bucket appears alongside phase-specific buckets, with `market_phase` key set to `"uncategorized"`, `label` set to `"Uncategorized / No Context"`, and `color_hex` set to `null`. Trades with a matching check-in but `market_phase = null` SHALL be grouped under a separate `phase_unset` bucket (key `"phase_unset"`, label `"Phase Not Set"`).

This replaces the previous `unmatched_trade_count` and `phase_unset_trade_count` exclusion approach. Instead of reporting excluded trade counts, uncategorized and phase-unset trades SHALL appear as explicit attribution buckets so the frontend can render them directly in the heatmap without additional logic.

#### Scenario: Unmatched trades appear as uncategorized bucket
- **WHEN** some trades have no matching `DailyCheckin` record
- **THEN** those trades are aggregated into an `uncategorized` bucket with `market_phase = "uncategorized"`, `label = "Uncategorized / No Context"`, `color_hex = null`

#### Scenario: Phase-unset trades appear as phase_unset bucket
- **WHEN** a trade has a matching `DailyCheckin` but `market_phase = null`
- **THEN** those trades are aggregated into a `phase_unset` bucket with `market_phase = "phase_unset"`, `label = "Phase Not Set"`, `color_hex = null`

#### Scenario: All trades have valid phases
- **WHEN** all trades in the date range have a check-in with a non-null `market_phase`
- **THEN** the response contains only phase-specific buckets — no `uncategorized` or `phase_unset` buckets appear

#### Scenario: Successful correlation request with default phases
- **WHEN** a user sends `GET /api/v1/portfolios/{portfolio_id}/analytics/correlations/market-phase` and their check-ins use only the four default phases
- **THEN** the system returns HTTP 200 with up to four `MarketPhaseCorrelation` buckets — one per distinct phase name observed in matched check-ins — with `label` and `color_hex` resolved from `MarketPhaseDefinition`. If uncategorized or phase-unset trades exist, those buckets appear as well.

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
- **THEN** the system returns HTTP 200 with a single `uncategorized` bucket containing all trades for the period

#### Scenario: Some trades have no matching check-in
- **WHEN** some trades' close dates have no matching `DailyCheckin`
- **THEN** those trades are aggregated into the `uncategorized` bucket alongside any phase-specific buckets for matched trades

#### Scenario: LEFT JOIN semantics — trades without check-ins go to uncategorized bucket
- **WHEN** a trade has no check-in on its close date
- **THEN** it SHALL be aggregated into the `uncategorized` bucket with `market_phase = "uncategorized"` and `label = "Uncategorized / No Context"`

### Requirement: Attribution response includes explicit uncategorized and phase_unset buckets
Trades without a check-in record SHALL be aggregated into an `uncategorized` bucket. Trades with a check-in but `market_phase = null` SHALL be aggregated into a `phase_unset` bucket. Both buckets increase the bucket count in the response — there are no separate exclusion counters.

#### Scenario: Response shape with partial match
- **WHEN** 10 trades are in the date range, 3 have no check-in, and 2 have a check-in with `market_phase = null`
- **THEN** the response includes an `uncategorized` bucket with 3 trades, a `phase_unset` bucket with 2 trades, and phase-specific buckets aggregating the remaining 5 trades

#### Scenario: All trades matched with phase
- **WHEN** all trades in the date range have a check-in with a non-null `market_phase`
- **THEN** no `uncategorized` or `phase_unset` buckets appear in the response

### Requirement: Attribution endpoint handles missing DailyCheckin table gracefully
If Spec 5 (Daily Check-in System) has not been deployed, the attribution endpoint SHALL not crash or return misleading data.

#### Scenario: daily_checkins table does not exist
- **WHEN** the attribution endpoint is called and the `daily_checkins` table is absent
- **THEN** the system returns HTTP 503 with `{"detail": "daily_checkins table not available — deploy Spec 5 first"}`

#### Scenario: daily_checkins table exists but is empty
- **WHEN** the table exists but has no rows for the user
- **THEN** the system returns HTTP 200 with a single `uncategorized` bucket containing all trades in range

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
