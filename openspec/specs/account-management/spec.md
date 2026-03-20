## ADDED Requirements

### Requirement: Account Type Specialization
The system MUST require an explicit `type` upon Account creation, strictly limited to an accepted enumeration (`MANUAL`, `SCHWAB`, `IBKR`).

#### Scenario: Creating a new account with a valid type
- **WHEN** the user creates an account with type `SCHWAB`
- **THEN** the system SHALL save the account and assign the `SCHWAB` type

### Requirement: Store Encrypted Account Properties
The system MUST be able to attach multiple secure key-value properties to an account and encrypt their values symmetrically before persisting to the database.

#### Scenario: Submitting Broker Credentials during Account Creation
- **WHEN** the user creates a `SCHWAB` account and provides an `app_key` and `app_secret`
- **THEN** the system SHALL encrypt both values using Fernet symmetric encryption
- **THEN** the system SHALL persist them to the `account_properties` table linked to the account

#### Scenario: Fetching Account details masks secure properties
- **WHEN** the user retrieves an account via GET `/api/v1/accounts`
- **THEN** the system SHALL NOT return the plain text values of the account properties
- **THEN** the system SHALL instead return a boolean indicator or masked string (e.g., `has_api_keys: true`)

## REMOVED Requirements

### Requirement: Global User Broker Connections
**Reason**: Broker connections are now scoped to individual accounts rather than globally per user.
**Migration**: Existing tokens in `broker_connections` will be dropped. Users must re-enter credentials per account.