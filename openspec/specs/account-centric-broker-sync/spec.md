# account-centric-broker-sync Specification

## Purpose
Define expected behavior for account-scoped broker API sync (IBKR and Schwab) and Schwab account resolution.

## Requirements

### Requirement: Execute API Sync per Account
The system MUST support initiating trade synchronization targeting a specific `account_id` utilizing the account's specific decrypted properties. For `SCHWAB` accounts, the sync SHALL fetch transactions from the Schwab Transactions API using the account's stored **OAuth access token** and import them through the shared `SchwabJSONParser` + raw-transaction FIFO pipeline (the same path as file upload), rather than the legacy Orders API + `SchwabOrderNormalizer` path.

#### Scenario: Syncing an IBKR Account
- **WHEN** the user initiates an API sync for an account of type `IBKR`
- **THEN** the system SHALL look up the account's decrypted Flex Token and Query ID
- **THEN** the system SHALL execute the IBKR sync logic

#### Scenario: Syncing a Schwab Account
- **WHEN** the user initiates an API sync for an account of type `SCHWAB`
- **THEN** the system SHALL look up the account's decrypted `SCHWAB_ACCESS_TOKEN` (refreshing it via the stored `SCHWAB_REFRESH_TOKEN` when expired or near expiry, and persisting the rotated token)
- **THEN** the system SHALL use that access token as the Bearer credential for the Schwab accounts and Transactions API calls
- **THEN** the system SHALL fetch transactions (`types=TRADE`) from the Schwab Transactions API for the resolved account
- **THEN** the system SHALL import the fetched transactions via `SchwabJSONParser.parse_raw()` and the raw-transaction FIFO pipeline
- **THEN** the system SHALL correctly produce `SHORT` trades for short round-trips

#### Scenario: Paginated transactions are merged
- **WHEN** the Schwab Transactions API returns results across multiple pages (next-page token or `Link` header)
- **THEN** the system SHALL iteratively fetch and concatenate all pages before importing, so no transactions are lost

#### Scenario: Date parameters formatted for the API
- **WHEN** the system builds the `startDate`/`endDate` query parameters for the Transactions API
- **THEN** it SHALL format them to the API-accepted format (`YYYY-MM-DDTHH:MM:SSZ`, without milliseconds) to avoid `400 Bad Request`

#### Scenario: Syncing without a connected Schwab account
- **WHEN** the user initiates an API sync for a `SCHWAB` account that has no stored `SCHWAB_ACCESS_TOKEN`/`SCHWAB_REFRESH_TOKEN`
- **THEN** the system SHALL return an HTTP 400 Bad Request indicating the account must be connected via the Schwab OAuth flow

#### Scenario: Syncing without valid credentials
- **WHEN** the user initiates an API sync for an account missing required `AccountProperty` records
- **THEN** the system SHALL return an HTTP 400 Bad Request indicating missing configuration

### Requirement: Schwab Sync Account Resolution
The Schwab online sync SHALL resolve the Schwab `accountHash` for the Transactions API by calling the Schwab accounts endpoint and matching against the target `Account.account_number`, applying the same matching semantics as the file-upload import.

#### Scenario: Configured account number matches a broker account
- **WHEN** the target Schwab account has `account_number` set and the accounts endpoint returns an entry whose `accountNumber` equals it
- **THEN** the system SHALL use that entry's `hashValue` to fetch transactions

#### Scenario: Configured account number does not match any broker account
- **WHEN** the target Schwab account has `account_number` set and no accounts-endpoint entry matches it
- **THEN** the system SHALL abort the sync with an error naming the configured account number and the available broker account number(s)

#### Scenario: Account number unset, single broker account
- **WHEN** the target Schwab account has no `account_number` set and the accounts endpoint returns exactly one account
- **THEN** the system SHALL use that account's `hashValue` to fetch transactions
- **THEN** the system SHALL persist that account's `accountNumber` onto the target `Account` row and emit an `account.account_number_bound` audit event

#### Scenario: Account number unset, multiple broker accounts
- **WHEN** the target Schwab account has no `account_number` set and the accounts endpoint returns more than one account
- **THEN** the system SHALL abort the sync with a message indicating multiple Schwab accounts were found, that no assignment is possible, and that the account number must be entered, listing the available account numbers
