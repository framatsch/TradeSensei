# account-management Specification

## Purpose
Define expected behavior for account creation, type specialization, encrypted account
properties, and portfolio-scoped currency inheritance.
## Requirements
### Requirement: Account Type Specialization
The system MUST require an explicit `type` upon Account creation, strictly limited to an accepted enumeration (`MANUAL`, `SCHWAB`, `IBKR`). Account creation additionally MUST require a valid `portfolio_id` owned by the requesting user. The created account SHALL be linked to that portfolio, and its currency MUST be inherited from the portfolio's `base_currency`. The user SHALL NOT be prompted for currency selection.

#### Scenario: Creating a new account with a valid type
- **WHEN** the user creates an account with type `SCHWAB` and a valid `portfolio_id`
- **THEN** the system SHALL save the account and assign the `SCHWAB` type
- **THEN** the account's `portfolio_id` SHALL be set to the provided value
- **THEN** the account's `currency` SHALL automatically be set to the portfolio's `base_currency`

#### Scenario: Creating an account without portfolio_id rejected
- **WHEN** the user creates an account without providing `portfolio_id`
- **THEN** the system SHALL return HTTP 422 Unprocessable Entity

#### Scenario: Creating an account with foreign portfolio_id rejected
- **WHEN** the user creates an account with a `portfolio_id` that belongs to another user
- **THEN** the system SHALL return HTTP 404

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

### Requirement: Danger Zone Clear-Trades Action
The account Danger Zone SHALL offer a "Clear all trades" destructive action that removes all trades for the account without deleting the account. The action SHALL be visually distinct as destructive and SHALL require an explicit confirmation affordance consistent with the account-deletion confirmation.

#### Scenario: Danger Zone exposes clear-trades
- **WHEN** a user opens the Danger Zone for an account they own
- **THEN** a "Clear all trades" action SHALL be presented alongside "Delete account"
- **THEN** the action SHALL clearly indicate it is destructive and cannot be undone

#### Scenario: Confirmation gate before clearing
- **WHEN** the user triggers "Clear all trades"
- **THEN** the user SHALL be required to confirm (acknowledgement or type-to-confirm) before the trades are deleted

#### Scenario: Account survives clear-trades
- **WHEN** the clear-trades action completes successfully
- **THEN** the account SHALL still exist and remain selectable
- **THEN** only its trades, executions, and raw transactions SHALL have been removed

