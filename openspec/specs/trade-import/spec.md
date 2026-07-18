# trade-import Specification

## Purpose
Define expected behavior for broker trade import, including trade detail enrichment with
taxonomies and annotations.
## Requirements
### Requirement: Trade detail includes assigned taxonomies
The system SHALL include the list of assigned taxonomies (with full definition data) in the trade detail response.

#### Scenario: Trade with taxonomies returns them
- **WHEN** a GET request retrieves a trade that has taxonomy assignments
- **THEN** the response contains a `taxonomies` array with each assigned taxonomy's definition data

#### Scenario: Archived taxonomy definition included when assigned
- **WHEN** a trade has an assignment to a taxonomy that was subsequently archived
- **THEN** the `taxonomies` array in the response still includes the archived taxonomy definition

### Requirement: Trade detail includes assigned annotations
The system SHALL include the list of assigned annotations (with definition data and typed value) in the trade detail response.

#### Scenario: Trade with annotations returns them
- **WHEN** a GET request retrieves a trade with annotation assignments
- **THEN** the response contains an `annotations` array with each annotation's definition and resolved `value`

#### Scenario: Annotation value is resolved from typed column
- **WHEN** an int-typed annotation is assigned with `value_int = 5`
- **THEN** the API response presents `value: 5` (not the raw column structure)

### Requirement: Clear All Trades for an Account
The system SHALL let an authenticated user delete ALL trades, executions, and raw transactions for an account they own, in a single transaction, without deleting the account itself and without requiring a file upload. The operation SHALL delete manually-edited trades as well (a true fresh start). It SHALL require an explicit acknowledgement flag and SHALL emit a manual audit event with safe counts only.

The "Clear All Trades" action SHALL be placed inside the account edit modal's Danger Zone (alongside the "Delete Account" action), NOT in the account list overview. Both destructive actions share the same Danger Zone region for consistency.

#### Scenario: Clearing trades leaves the account intact
- **WHEN** an authenticated user requests to clear all trades for an account they own with `acknowledged=true`
- **THEN** the system SHALL delete all trades, executions, and raw transactions for that account
- **THEN** the account row itself SHALL remain, with its type, credentials, and settings unchanged
- **THEN** the system SHALL return the counts of deleted trades and executions

#### Scenario: Manually-edited trades are also removed
- **WHEN** the account contains one or more manually-edited trades and the user clears all trades
- **THEN** the manually-edited trades SHALL be deleted along with the imported trades

#### Scenario: Acknowledgement is required
- **WHEN** the user requests to clear all trades without `acknowledged=true`
- **THEN** the system SHALL return HTTP 400 and SHALL NOT delete any data

#### Scenario: Account owned by another user
- **WHEN** the user requests to clear trades for an account that belongs to a different user
- **THEN** the system SHALL return HTTP 404 and SHALL NOT delete any data

#### Scenario: Failure rolls back
- **WHEN** an error occurs partway through deleting trades, executions, or raw transactions
- **THEN** the entire operation SHALL roll back, leaving all data unchanged

#### Scenario: Audit event carries only safe metadata
- **WHEN** a clear-all-trades operation completes
- **THEN** the system SHALL emit an `account.trades_cleared` audit event containing only safe identifiers and counts (account_id, trades_deleted, executions_deleted)
- **THEN** the audit event SHALL NOT include P&L, prices, quantities, or notes

### Requirement: Generic Broker-Agnostic Import Date Range Control
The import UI SHALL present a single, broker-agnostic date-range control for all broker types that support timed sync. Broker-specific differences SHALL be supplied by a per-broker capability descriptor (maximum window in days and the sync parameter name/shape) rather than per-broker conditional branches in the component tree.

#### Scenario: IBKR and Schwab share the same control
- **WHEN** an IBKR account or a Schwab account is selected for import
- **THEN** the same date-range control (fill bar plus YTD/custom toggle) SHALL be rendered for both

#### Scenario: Broker maximum window is enforced from the descriptor
- **WHEN** a broker's capability descriptor declares a maximum window of N days
- **THEN** the control SHALL clamp custom date selection to that window and SHALL display the appropriate limit indicator

#### Scenario: Adding a new broker requires no new UI branch
- **WHEN** a new broker is added with a capability descriptor (max window, sync parameter)
- **THEN** the import date-range control SHALL work for that broker without adding a broker-specific conditional to the component

#### Scenario: Correct sync parameter is produced per broker
- **WHEN** the user confirms a sync for a given broker account
- **THEN** the control SHALL produce the sync request parameter in the shape declared by that broker's descriptor (e.g. an absolute `from_date` for IBKR, a `days` window for Schwab)

### Requirement: Destructive Account Reset
The file-coupled fresh-start affordance SHALL be superseded by the standalone "Clear All Trades" action for the "reset an account" use case. Resetting an account's trades SHALL be possible independently of whether a broker file is being imported.

#### Scenario: Reset without a file
- **WHEN** a user wants to reset an account's trades and has no broker file to upload
- **THEN** the user SHALL be able to clear all trades via the standalone clear-trades action
- **THEN** the user SHALL NOT be required to upload a file to reset the account

#### Scenario: Re-import after clearing
- **WHEN** a user clears all trades and later uploads a broker file for the same account
- **THEN** the normal import flow SHALL import the file's trades into the now-empty account

