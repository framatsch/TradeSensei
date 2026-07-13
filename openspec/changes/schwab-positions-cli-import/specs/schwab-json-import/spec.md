## MODIFIED Requirements

### Requirement: Schwab JSON File Upload
The system SHALL accept `.json` files for Schwab accounts via the existing `POST /api/v1/imports/upload` endpoint, where the file is a wrapped payload of the form `{fetchedAt, dateRange, accounts:[{accountNumber, accountHash, positions, transactions}]}`.

#### Scenario: Valid wrapped JSON file uploaded for Schwab account
- **WHEN** a user uploads a wrapped `.json` file to `POST /api/v1/imports/upload` with a Schwab account
- **THEN** the system SHALL parse the file using `SchwabJSONParser.parse_raw()`
- **THEN** the system SHALL read transactions from `accounts[].transactions`
- **THEN** the system SHALL create `BrokerRawTransaction` rows with PK `"{user_id}:schwab:{activityId}"`
- **THEN** the system SHALL run the FIFO aggregation pipeline and return an `ImportResult`

#### Scenario: Non-TRADE transactions filtered
- **WHEN** the wrapped file's `accounts[].transactions` contains entries with `type != "TRADE"` or `status` not in `{COMPLETED, VALID}`
- **THEN** the system SHALL skip those entries and NOT create `BrokerRawTransaction` rows for them

#### Scenario: Re-upload of same file (idempotency)
- **WHEN** the same JSON file is uploaded a second time
- **THEN** the system SHALL NOT create duplicate `BrokerRawTransaction` rows (ON CONFLICT DO NOTHING)
- **THEN** the system SHALL return an `ImportResult` with `raw_transactions_created = 0` for the duplicate records

#### Scenario: CSV file uploaded for SCHWAB account (deprecated path)
- **WHEN** a user uploads a `.csv` file to `POST /api/v1/imports/upload` with a Schwab account
- **THEN** the system SHALL return HTTP 422 with message "Schwab accounts require JSON format (.json). CSV import is no longer supported."

#### Scenario: Any file uploaded for MANUAL account
- **WHEN** a user attempts to upload any file to `POST /api/v1/imports/upload` with a MANUAL account
- **THEN** the system SHALL return HTTP 422 with message "File import is not supported for manual accounts"

#### Scenario: JSON file with invalid structure
- **WHEN** the uploaded file is not a valid JSON object with an `accounts` array, or an account entry is missing required fields (`accountNumber`, `transactions`)
- **THEN** the system SHALL return HTTP 422 with a descriptive error message

#### Scenario: Legacy top-level array is rejected
- **WHEN** the uploaded file is a bare top-level JSON array of transactions (the legacy format)
- **THEN** the system SHALL return HTTP 422 with a descriptive error message indicating the wrapped `{accounts:[...]}` format is required

---

### Requirement: Schwab JSON REST Endpoint
The system SHALL provide a dedicated `POST /api/v1/imports/schwab-json` endpoint that accepts a wrapped Schwab payload (`{fetchedAt, dateRange, accounts:[...]}`) as the request body.

#### Scenario: Valid wrapped JSON body import
- **WHEN** a client sends a `POST /api/v1/imports/schwab-json?account_id={id}` with a wrapped JSON object body
- **THEN** the system SHALL validate the account exists and is of type `SCHWAB`
- **THEN** the system SHALL parse the body using `SchwabJSONParser.parse_raw()`
- **THEN** the system SHALL run the full raw-data import pipeline and return an `ImportResult`

#### Scenario: Account not SCHWAB type
- **WHEN** the `account_id` refers to a non-SCHWAB account
- **THEN** the system SHALL return HTTP 422 with message "Account type must be SCHWAB for this endpoint"

#### Scenario: Empty accounts array
- **WHEN** the request body has an empty `accounts` array
- **THEN** the system SHALL return HTTP 200 with `ImportResult` showing `raw_transactions_created = 0` and `trades_created = 0`

---

### Requirement: Schwab JSON Parser — Instruction Mapping
The `SchwabJSONParser` SHALL correctly map the Schwab `instruction`/`positionEffect` field to `direction` and quantity sign, reading from transactions in `accounts[].transactions`.

#### Scenario: BUY instruction maps to LONG opening
- **WHEN** a transaction has `instruction = "BUY"` (or an opening equity leg)
- **THEN** the parser SHALL set `direction = "LONG"` and `quantity > 0`

#### Scenario: SELL instruction maps to LONG closing
- **WHEN** a transaction has `instruction = "SELL"` (or a closing equity leg)
- **THEN** the parser SHALL set `direction = "LONG"` and `quantity > 0`

#### Scenario: SELL_SHORT instruction maps to SHORT opening
- **WHEN** a transaction has `instruction = "SELL_SHORT"`
- **THEN** the parser SHALL set `direction = "SHORT"` and `quantity > 0`

#### Scenario: BUY_TO_COVER instruction maps to SHORT closing
- **WHEN** a transaction has `instruction = "BUY_TO_COVER"`
- **THEN** the parser SHALL set `direction = "SHORT"` and `quantity > 0`

#### Scenario: Unknown instruction is skipped
- **WHEN** a transaction has an unrecognized `instruction` value
- **THEN** the parser SHALL skip that record and log a warning with the `activityId`

---

### Requirement: Schwab JSON Parser — Transaction Extraction
The `SchwabJSONParser` SHALL extract each execution from the `transferItems` array of the transactions carried under `accounts[].transactions`.

#### Scenario: transferItems format (array)
- **WHEN** a transaction object has a `transferItems` key with an array of leg objects
- **THEN** the parser SHALL use the first leg with a non-empty `instrument.symbol` as the primary execution leg
- **THEN** commission/fee legs (identified by `feeType` and no security symbol) SHALL be summed and stored as `commission`

#### Scenario: time field parsed as UTC
- **WHEN** a transaction has a `time` field with a UTC offset (e.g. `+0000`)
- **THEN** the parser SHALL parse it as a timezone-aware datetime and convert to UTC

## ADDED Requirements

### Requirement: Schwab Import Account-Number Matching
The Schwab import SHALL validate the file's account(s) against the target Trade Sensei `Account.account_number` and abort on mismatch or ambiguity.

#### Scenario: Account number set and matches
- **WHEN** the target Trade Sensei Schwab account has `account_number` set and one of the file's `accounts[].accountNumber` values equals it
- **THEN** the system SHALL import that matching account's transactions

#### Scenario: Account number set and does not match
- **WHEN** the target Trade Sensei Schwab account has `account_number` set and no `accounts[].accountNumber` in the file matches it
- **THEN** the system SHALL abort the import with HTTP 422 and a descriptive error naming the configured account number and the account number(s) present in the file

#### Scenario: Account number unset, single account in file
- **WHEN** the target Trade Sensei Schwab account has no `account_number` set and the file contains exactly one account entry
- **THEN** the system SHALL import that single account's transactions
- **THEN** the system SHALL persist that account entry's `accountNumber` onto the target `Account` row so subsequent imports match automatically

#### Scenario: Account number unset, multiple accounts in file
- **WHEN** the target Trade Sensei Schwab account has no `account_number` set and the file contains more than one account entry
- **THEN** the system SHALL abort the import with HTTP 422 and a descriptive error listing the available `accountNumber` values in the file

## REMOVED Requirements

### Requirement: Schwab JSON Parser — Dual Format Support
**Reason**: The importer now accepts only the wrapped `{fetchedAt, dateRange, accounts:[...]}` schema. The flat top-level `transactionItem` array format and the standalone `transferItems`-vs-`transactionItem` dual handling are no longer supported, and the `transactionDate` (`-05:00` offset) fixture shape is replaced by the API's `time` field.
**Migration**: Regenerate Schwab exports with `tools/schwab_cli.py positions`, which produces the wrapped format. Existing top-level-array files must be re-exported; they will be rejected with HTTP 422.
