## MODIFIED Requirements

### Requirement: Execute API Sync per Account

The system MUST support initiating trade synchronization targeting a specific `account_id` utilizing the account's specific decrypted properties. Both broker syncs SHALL fetch their payload from the broker API and import it through `ImportService.import_trades()` and the shared raw-transaction FIFO pipeline — the same path as file upload — rather than through any broker-specific parsing or persistence implementation.

For `SCHWAB` accounts, the sync SHALL fetch transactions from the Schwab Transactions API using the account's stored **OAuth access token** and import them through the shared `SchwabJSONParser` + raw-transaction FIFO pipeline, rather than the legacy Orders API + `SchwabOrderNormalizer` path.

For `IBKR` accounts, the sync SHALL fetch the Flex Query XML from the IBKR Flex Web Service and import it through the shared `IBKRXMLParser` + raw-transaction FIFO pipeline. The Flex client SHALL NOT parse, aggregate, deduplicate, or persist trade data.

#### Scenario: Syncing an IBKR Account
- **WHEN** the user initiates an API sync for an account of type `IBKR`
- **THEN** the system SHALL look up the account's decrypted Flex Token and Query ID
- **THEN** the system SHALL fetch the Flex Query XML from the IBKR Flex Web Service
- **THEN** the system SHALL import that XML via `ImportService.import_trades()` with `BrokerType.IBKR`
- **THEN** the sync SHALL create raw transactions and logical executions, and link executions to their trades

#### Scenario: IBKR sync respects protected trades
- **GIVEN** a metadata-protected trade in the target account
- **WHEN** an IBKR account sync runs
- **THEN** the protected trade SHALL be isolated from the projection rebuild exactly as during a file upload
- **THEN** no sentinel orphan trade SHALL be created for a contract held by that trade
- **THEN** protection outcomes SHALL be reported in the sync result

#### Scenario: Syncing a Schwab Account
- **WHEN** the user initiates an API sync for an account of type `SCHWAB`
- **THEN** the system SHALL look up the account's decrypted `SCHWAB_ACCESS_TOKEN` (refreshing it via the stored `SCHWAB_REFRESH_TOKEN` when expired or near expiry, and persisting the rotated token)
- **THEN** the system SHALL use that access token as the Bearer credential for the Schwab accounts and Transactions API calls
- **THEN** the system SHALL fetch transactions (`types=TRADE`) from the Schwab Transactions API for the resolved account
- **THEN** the system SHALL import the fetched transactions via `ImportService.import_trades()` using `SchwabJSONParser.parse_raw()` and the raw-transaction FIFO pipeline
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

## ADDED Requirements

### Requirement: Sync results report protection outcomes for every broker

An account sync SHALL surface the protection counters produced by the import (`trades_protected_reconciled`, `trades_protected_skipped`, and unlinked-execution reporting) in its result, for every supported broker, so a protection-driven outcome is never silent regardless of ingestion path.

#### Scenario: IBKR sync surfaces protection counters

- **WHEN** an IBKR account sync completes
- **THEN** the sync result SHALL include the protection counters and warnings returned by the import

#### Scenario: Schwab sync surfaces protection counters

- **WHEN** a Schwab account sync completes
- **THEN** the sync result SHALL include the protection counters and warnings returned by the import
