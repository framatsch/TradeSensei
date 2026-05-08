## MODIFIED Requirements

### Requirement: Account Type Specialization
The system MUST require an explicit `type` upon Account creation, strictly limited to an accepted enumeration (`MANUAL`, `SCHWAB`, `IBKR`). Account creation additionally MUST require a valid `portfolio_id` owned by the requesting user. The created account SHALL be linked to that portfolio.

After successfully persisting a new user, the system SHALL automatically seed default records for that user within the same database transaction:
- Three `CheckinFieldDefinition` rows: `mood-level` (integer), `focus` (integer), `rule-followed` (boolean)
- Four `MarketPhaseDefinition` rows: `bullish` (label: "Bullish", color: #22c55e), `bearish` (label: "Bearish", color: #ef4444), `sideways` (label: "Sideways", color: #f59e0b), `volatile` (label: "Volatile", color: #8b5cf6)

Seeding SHALL be idempotent — if default records already exist for the user, the operation SHALL succeed without creating duplicates.

#### Scenario: Creating a new account with a valid type
- **WHEN** the user creates an account with type `SCHWAB` and a valid `portfolio_id`
- **THEN** the system SHALL save the account and assign the `SCHWAB` type
- **THEN** the account's `portfolio_id` SHALL be set to the provided value

#### Scenario: Creating an account without portfolio_id rejected
- **WHEN** the user creates an account without providing `portfolio_id`
- **THEN** the system SHALL return HTTP 422 Unprocessable Entity

#### Scenario: Creating an account with foreign portfolio_id rejected
- **WHEN** the user creates an account with a `portfolio_id` that belongs to another user
- **THEN** the system SHALL return HTTP 404

#### Scenario: Default field definitions and market phases seeded on registration
- **WHEN** a new user successfully registers
- **THEN** the system SHALL create three `CheckinFieldDefinition` records (`mood-level` integer, `focus` integer, `rule-followed` boolean) and four `MarketPhaseDefinition` records (`bullish`, `bearish`, `sideways`, `volatile`), all with `is_active=true`

#### Scenario: Registration rollback also rolls back field seeding
- **WHEN** the user registration transaction fails after the user record is written but before commit
- **THEN** no `CheckinFieldDefinition` records SHALL be persisted for that user

### Requirement: Store Encrypted Account Properties
The system MUST be able to attach multiple secure key-value properties to an account and encrypt their values symmetrically before persisting to the database.

#### Scenario: Submitting Broker Credentials during Account Creation
- **WHEN** the user creates a `SCHWAB` account and provides an `app_key` and `app_secret`
- **THEN** the system SHALL encrypt both values using Fernet symmetric encryption
- **THEN** the system SHALL persist them to the `account_properties` table linked to the account

#### Scenario: Fetching Account details masks secure properties
- **WHEN** the user retrieves an account via `GET /api/v1/portfolios/{portfolio_id}/accounts`
- **THEN** the system SHALL NOT return the plain text values of the account properties
- **THEN** the system SHALL instead return a boolean indicator or masked string (e.g., `has_api_keys: true`)

## REMOVED Requirements

### Requirement: Global User Broker Connections
**Reason**: Broker connections are now scoped to individual accounts rather than globally per user.
**Migration**: Existing tokens in `broker_connections` will be dropped. Users must re-enter credentials per account.
