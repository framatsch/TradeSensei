## ADDED Requirements

### Requirement: Conflict Banner on Trade Detail
The Trade Detail page SHALL display a prominent amber warning banner when `trade.has_conflict` is true.

#### Scenario: Banner display
- **WHEN** a user opens a trade with `has_conflict: true`
- **THEN** an amber banner MUST appear below the trade header
- **AND** the banner MUST contain: a warning icon, the title "Position Conflict", an explanation ("The logical execution totals don't match the broker's open position data. Review the execution legs below and adjust."), a "Dismiss" button (hides banner for this session, does not clear the flag), a "Help" link to the conflict resolution help page

#### Scenario: Banner hidden for non-conflicting trades
- **WHEN** a user opens a trade with `has_conflict: false`
- **THEN** no conflict banner MUST be displayed

### Requirement: Conflict Badge on Trade Row
The `TradeRow` component SHALL display a warning indicator when the trade has a conflict.

#### Scenario: Badge display in trade list
- **WHEN** a trade in the trade list has `has_conflict: true`
- **THEN** a small amber warning icon (⚠) MUST appear next to the symbol in that row

#### Scenario: No badge for non-conflicting trades
- **WHEN** a trade has `has_conflict: false`
- **THEN** no warning icon MUST be displayed

### Requirement: Needs Review System Filter
The system SHALL provide a system-level saved filter named "Needs Review" that shows only trades with conflicts.

#### Scenario: Filter creation
- **WHEN** the application initializes
- **THEN** a saved filter with `name: "Needs Review"`, `scope: SYSTEM`, and `definition: {"has_conflict": true}` MUST exist

#### Scenario: Filter in sidebar
- **WHEN** the sidebar renders the "TRADING LOG > Trades" section
- **THEN** "Needs Review" MUST appear as a sub-item alongside existing filters (All Losers, All Winners, etc.)
- **AND** it MUST display a count badge showing the number of conflicted trades

#### Scenario: Clicking the filter
- **WHEN** a user clicks "Needs Review" in the sidebar
- **THEN** the trade list MUST filter to show only trades where `has_conflict: true`

### Requirement: Backend has_conflict Filter Support
The trade listing endpoint SHALL support filtering by the `has_conflict` field.

#### Scenario: Filtering conflicted trades
- **WHEN** a user requests `GET /api/v1/trades?has_conflict=true`
- **THEN** the response MUST contain only trades with `has_conflict: true`

#### Scenario: TradeRead includes has_conflict
- **WHEN** a `TradeRead` response is serialized
- **THEN** it MUST include the `has_conflict` boolean field

### Requirement: Conflict Auto-Resolution
When execution mutations resolve a position conflict, the `has_conflict` flag SHALL be automatically cleared during re-aggregation.

#### Scenario: Conflict cleared after adding missing execution
- **WHEN** a user adds an execution that resolves the position discrepancy
- **AND** the re-aggregation detects no remaining quantity mismatch
- **THEN** the `has_conflict` flag MUST be set to `false` on the trade
- **AND** the conflict banner MUST disappear on the next page refresh
