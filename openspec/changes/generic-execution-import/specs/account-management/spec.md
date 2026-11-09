## MODIFIED Requirements

### Requirement: Account Type Specialization
The system MUST require an explicit `type` upon Account creation, strictly limited to an accepted enumeration (`MANUAL`, `SCHWAB`, `IBKR`, `GENERIC`). Account creation additionally MUST require a valid `portfolio_id` owned by the requesting user. The created account SHALL be linked to that portfolio, and its currency MUST be inherited from the portfolio's `base_currency`. The user SHALL NOT be prompted for currency selection. A `GENERIC` account SHALL support file import in the Trade Sensei Execution Format only and SHALL NOT require or accept broker API credentials.

#### Scenario: Creating a new account with a valid type
- **WHEN** the user creates an account with type `SCHWAB` and a valid `portfolio_id`
- **THEN** the system SHALL save the account and assign the `SCHWAB` type
- **THEN** the account's `portfolio_id` SHALL be set to the provided value
- **THEN** the account's `currency` SHALL automatically be set to the portfolio's `base_currency`

#### Scenario: Creating a generic account
- **WHEN** the user creates an account with type `GENERIC` and a valid `portfolio_id`
- **THEN** the system SHALL save the account with type `GENERIC` and SHALL NOT require any credentials

#### Scenario: Creating an account without portfolio_id rejected
- **WHEN** the user creates an account without providing `portfolio_id`
- **THEN** the system SHALL return HTTP 422 Unprocessable Entity

#### Scenario: Creating an account with foreign portfolio_id rejected
- **WHEN** the user creates an account with a `portfolio_id` that belongs to another user
- **THEN** the system SHALL return HTTP 404
