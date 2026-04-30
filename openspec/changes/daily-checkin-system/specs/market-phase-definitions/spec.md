## ADDED Requirements

### Requirement: Create a market phase definition
The system SHALL allow an authenticated user to create a `MarketPhaseDefinition` via POST `/api/v1/market-phases`. The record SHALL require `name` (string, max 50 chars, unique per user globally regardless of `is_active` status, lowercase kebab-case — this is the stable storage key used in `DailyCheckin.market_phase`) and `label` (string, max 100 chars — the human-readable display name). Optional `color_hex` (6-digit hex string, default `#6366f1`). `is_active` SHALL default to `true`.

The `name` field is **immutable after creation**. The `label` and `color_hex` fields are freely editable. A user SHALL NOT be able to create two definitions with the same `name`, even if the existing definition is inactive.

#### Scenario: Successful creation
- **WHEN** an authenticated user sends POST `/api/v1/market-phases` with `name="trending"`, `label="Trending"`, `color_hex="#22c55e"`
- **THEN** the system SHALL persist the definition and return HTTP 201

#### Scenario: Duplicate name rejected (including inactive)
- **WHEN** an authenticated user sends POST `/api/v1/market-phases` with a `name` that already exists for that user (regardless of `is_active`)
- **THEN** the system SHALL return HTTP 409 Conflict

#### Scenario: Invalid name format rejected
- **WHEN** an authenticated user sends POST `/api/v1/market-phases` with `name` containing uppercase letters or spaces
- **THEN** the system SHALL return HTTP 422 Unprocessable Entity

### Requirement: List market phase definitions
The system SHALL allow an authenticated user to list their `MarketPhaseDefinition` records via GET `/api/v1/market-phases`. An optional `is_active` query parameter SHALL filter results. Only the requesting user's records SHALL be returned. Results SHALL be ordered by `created_at` ascending (default creation order reflects the user's preferred display order).

#### Scenario: List all definitions
- **WHEN** an authenticated user sends GET `/api/v1/market-phases`
- **THEN** the system SHALL return HTTP 200 with all phase definitions for that user

#### Scenario: Filter by active status
- **WHEN** an authenticated user sends GET `/api/v1/market-phases?is_active=true`
- **THEN** the system SHALL return only definitions with `is_active=true`

### Requirement: Update a market phase definition
The system SHALL allow an authenticated user to update `label`, `color_hex`, or `is_active` via PATCH `/api/v1/market-phases/{id}`. The `name` field SHALL NOT be changeable after creation (it is the storage key used in persisted `DailyCheckin.market_phase` values — changing it would orphan historical records).

#### Scenario: Rename the display label
- **WHEN** an authenticated user sends PATCH `/api/v1/market-phases/{id}` with `{"label": "Strong Trend"}`
- **THEN** the system SHALL update only `label` and return HTTP 200

#### Scenario: Deactivate a phase
- **WHEN** an authenticated user sends PATCH `/api/v1/market-phases/{id}` with `{"is_active": false}`
- **THEN** the system SHALL update `is_active` and return HTTP 200. Existing `DailyCheckin` records that reference this phase name are NOT affected (historical data is preserved).

#### Scenario: name change rejected
- **WHEN** an authenticated user sends PATCH `/api/v1/market-phases/{id}` with `{"name": "new-name"}`
- **THEN** the system SHALL return HTTP 422 Unprocessable Entity indicating `name` is immutable

#### Scenario: Cross-user update rejected
- **WHEN** a user sends PATCH `/api/v1/market-phases/{id}` where the definition belongs to another user
- **THEN** the system SHALL return HTTP 404

### Requirement: Default market phase definitions seeded at registration
The system SHALL seed four default `MarketPhaseDefinition` records for every new user within the same database transaction as user registration. Seeding SHALL be idempotent.

#### Scenario: Default phases present after registration
- **WHEN** a new user successfully registers
- **THEN** the system SHALL create four `MarketPhaseDefinition` records: `bullish` (label: "Bullish", color: #22c55e), `bearish` (label: "Bearish", color: #ef4444), `sideways` (label: "Sideways", color: #f59e0b), `volatile` (label: "Volatile", color: #8b5cf6) — all with `is_active=true`

#### Scenario: Registration rollback also rolls back phase seeding
- **WHEN** the user registration transaction fails before commit
- **THEN** no `MarketPhaseDefinition` records SHALL be persisted for that user

### Requirement: market_phase on DailyCheckin is validated against user's active definitions
When creating or updating a `DailyCheckin`, the system SHALL validate that `market_phase` matches the `name` of an active `MarketPhaseDefinition` owned by the requesting user. Validation SHALL load phase definitions inside the same DB transaction as the check-in write.

#### Scenario: Valid phase accepted
- **WHEN** an authenticated user submits a check-in with `market_phase: "bullish"` and an active `MarketPhaseDefinition` with `name="bullish"` exists for that user
- **THEN** the system SHALL persist the check-in

#### Scenario: Unknown phase name rejected
- **WHEN** an authenticated user submits a check-in with `market_phase: "TRENDING"` and no active definition with `name="TRENDING"` exists
- **THEN** the system SHALL return HTTP 422 with a message identifying the unknown phase name

#### Scenario: Historical check-ins with deactivated phase are preserved
- **WHEN** a `MarketPhaseDefinition` is deactivated after check-ins were recorded using that phase name
- **THEN** existing `DailyCheckin` records retaining that phase name SHALL remain intact and readable
