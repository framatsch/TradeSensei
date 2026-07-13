## ADDED Requirements

### Requirement: Schwab CLI Tool
The system SHALL provide a command-line tool at `tools/schwab_cli.py` that authenticates to the Charles Schwab Trader API and exposes subcommands to list accounts, fetch positions, fetch transactions, and refresh OAuth tokens. The `positions` subcommand SHALL write positions and transactions to a JSON file in the wrapped import schema (`{fetchedAt, accounts:[...]}`).

#### Scenario: Positions subcommand writes wrapped JSON file
- **WHEN** a user runs `python tools/schwab_cli.py positions` with valid Schwab credentials configured
- **THEN** the tool SHALL authenticate via Schwab OAuth 2.0
- **THEN** the tool SHALL fetch positions and transactions for the resolved account(s)
- **THEN** the tool SHALL write a JSON file whose top-level object contains `fetchedAt` and an `accounts` array, each entry containing `accountNumber`, `accountHash`, `positions`, and `transactions`

#### Scenario: Missing credentials aborts with clear error
- **WHEN** `SCHWAB_APP_KEY` or `SCHWAB_APP_SECRET` is not configured
- **THEN** the tool SHALL exit with a non-zero status and print a message naming the missing environment variable(s)

#### Scenario: Transactions subcommand date range controls the window
- **WHEN** the user runs the `transactions` subcommand with `--start YYYY-MM-DD` and/or `--end YYYY-MM-DD`
- **THEN** the tool SHALL fetch transactions only within that window and record the window in the output file's `dateRange`
- **WHEN** the user omits `--start` and/or `--end`
- **THEN** the tool SHALL default to a recent window (the last 90 days ending today)

#### Scenario: Accounts subcommand lists linked accounts
- **WHEN** the user runs `python tools/schwab_cli.py accounts`
- **THEN** the tool SHALL print each linked account's number and hash without writing an output file

---

### Requirement: Schwab CLI Account Resolution
Each fetch subcommand SHALL resolve its target account(s) using an optional `--account/-a` argument that refers to the Schwab account number, aborting on ambiguity so the output file matches the importer's expectations.

#### Scenario: Single linked account is auto-selected
- **WHEN** the linked Schwab login exposes exactly one account and `--account` is omitted
- **THEN** the tool SHALL select that account automatically and proceed

#### Scenario: Multiple accounts without --account aborts and lists options
- **WHEN** the linked Schwab login exposes more than one account and `--account` is omitted
- **THEN** the tool SHALL exit with a non-zero status without fetching
- **THEN** the tool SHALL print the available account numbers so the user can re-run with `--account`

#### Scenario: Explicit --account selects the matching account
- **WHEN** the user passes `--account` matching one of the linked account numbers
- **THEN** the tool SHALL fetch only that account and write a single-account output file

#### Scenario: Explicit --account does not match any linked account
- **WHEN** the user passes `--account` that does not match any linked account number
- **THEN** the tool SHALL exit with a non-zero status
- **THEN** the tool SHALL print an error and the list of available account numbers

---

### Requirement: Open positions derive from downloaded transactions
The CLI's output SHALL be sufficient for the importer to surface currently-open positions as open trades **without** parsing the `positions[]` snapshot, provided the fetched transaction window includes each open position's opening transaction.

#### Scenario: Open holding appears via its opening transaction
- **WHEN** an account holds an open position whose opening `TRADE` (`positionEffect = "OPENING"`) falls within the fetched date range
- **THEN** that opening transaction SHALL be present in the output file's `accounts[].transactions`
- **THEN** importing the file SHALL leave the instrument as an open lot (the FIFO aggregator finds no matching close)

#### Scenario: Position opened before the window is not surfaced
- **WHEN** an open position's opening transaction predates the fetched date range and is therefore absent from `transactions`
- **THEN** the position SHALL NOT appear as an open trade after import
- **THEN** the documentation SHALL instruct the user to widen `--start` to include the opening transaction

---

### Requirement: Schwab CLI Documentation
The system SHALL provide user-facing documentation for the CLI tool so that an end user can download their trades and then import them into Trade Sensei.

#### Scenario: Documentation describes the full workflow
- **WHEN** a user reads the tool documentation
- **THEN** the documentation SHALL describe required environment variables, how to run each subcommand, the `--account`/`--start`/`--end`/`--output` arguments, the output file location and format, the note that open positions require their opening transaction to be within the fetched window, and how to import the resulting file into Trade Sensei

#### Scenario: Tools reference lists the tool
- **WHEN** a user reads `tools/README.md`
- **THEN** the reference SHALL list `schwab_cli.py` with a one-line description and a link to its documentation
