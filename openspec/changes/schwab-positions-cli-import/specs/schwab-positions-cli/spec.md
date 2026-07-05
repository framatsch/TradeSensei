## ADDED Requirements

### Requirement: Schwab Positions CLI Tool
The system SHALL provide a command-line tool at `tools/schwab_get_positions.py` that authenticates to the Charles Schwab Trader API, fetches positions and transactions for a single target account, and writes them to a JSON file in the wrapped import schema (`{fetchedAt, dateRange, accounts:[...]}`).

#### Scenario: Successful fetch writes wrapped JSON file
- **WHEN** a user runs `python tools/schwab_get_positions.py` with valid Schwab credentials configured
- **THEN** the tool SHALL authenticate via Schwab OAuth 2.0
- **THEN** the tool SHALL fetch positions and transactions for the resolved account
- **THEN** the tool SHALL write a JSON file whose top-level object contains `fetchedAt`, `dateRange`, and an `accounts` array with exactly one account entry containing `accountNumber`, `accountHash`, `positions`, and `transactions`

#### Scenario: Missing credentials aborts with clear error
- **WHEN** `SCHWAB_APP_KEY` or `SCHWAB_APP_SECRET` is not configured
- **THEN** the tool SHALL exit with a non-zero status and print a message naming the missing environment variable(s)

#### Scenario: Date range arguments control the transaction window
- **WHEN** the user passes `--start YYYY-MM-DD` and/or `--end YYYY-MM-DD`
- **THEN** the tool SHALL fetch transactions only within that window and record the window in the output file's `dateRange`
- **WHEN** the user omits `--start` and/or `--end`
- **THEN** the tool SHALL default to a sensible recent window (e.g. the last 30 days ending today)

---

### Requirement: Schwab Positions CLI Account Resolution
The tool SHALL resolve exactly one target account before fetching, using an optional `--account-id` argument that refers to the Schwab account number.

#### Scenario: Single linked account is auto-selected
- **WHEN** the linked Schwab login exposes exactly one account and `--account-id` is omitted
- **THEN** the tool SHALL select that account automatically and proceed

#### Scenario: Multiple accounts without --account-id aborts and lists options
- **WHEN** the linked Schwab login exposes more than one account and `--account-id` is omitted
- **THEN** the tool SHALL exit with a non-zero status without fetching
- **THEN** the tool SHALL print the available account numbers so the user can re-run with `--account-id`

#### Scenario: Explicit --account-id selects the matching account
- **WHEN** the user passes `--account-id` matching one of the linked account numbers
- **THEN** the tool SHALL fetch only that account and write a single-account output file

#### Scenario: Explicit --account-id does not match any linked account
- **WHEN** the user passes `--account-id` that does not match any linked account number
- **THEN** the tool SHALL exit with a non-zero status
- **THEN** the tool SHALL print an error and the list of available account numbers

---

### Requirement: Schwab Positions CLI Documentation
The system SHALL provide user-facing documentation for the CLI tool so that an end user can download their trades and then import them into Trade Sensei.

#### Scenario: Documentation describes the full workflow
- **WHEN** a user reads the tool documentation
- **THEN** the documentation SHALL describe required environment variables, how to run the tool, the `--account-id`/`--start`/`--end`/`--output` arguments, the output file location (default `./tmp/positions.json`) and format, and how to import the resulting file into Trade Sensei

#### Scenario: Tools reference lists the tool
- **WHEN** a user reads `tools/README.md`
- **THEN** the reference SHALL list `schwab_get_positions.py` with a one-line description and a link to its documentation
