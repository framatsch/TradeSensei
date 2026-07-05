## Why

Trade Sensei users cannot easily get their live Schwab trades into the platform: there is no CLI tool to pull them, and the Schwab JSON importer only accepts a bare top-level array of transactions — not the wrapped `{fetchedAt, dateRange, accounts:[...]}` payload that the Schwab Trader API actually returns. The result is a manual, error-prone gap between "I have a Schwab account" and "my trades are in Trade Sensei." This change closes that gap end-to-end: run one command to download your current trades, then import the resulting file directly.

## What Changes

- Add a `tools/schwab_get_positions.py` CLI tool (repo root, mirroring `tools/reset_password.py`) that authenticates with Schwab, fetches positions + transactions, and writes a JSON file in the wrapped schema documented in `positions_schema.md`.
  - Add an `--account-id` (Schwab account number) argument. If the linked login exposes exactly one account, use it automatically; if it exposes more than one and `--account-id` is omitted, **abort** and print the available account numbers.
- **BREAKING**: Change the Schwab JSON importer (`SchwabJSONParser`) to accept **only** the wrapped format `{fetchedAt, dateRange, accounts:[{accountNumber, accountHash, positions, transactions}]}`. The legacy top-level-array input is no longer accepted.
  - Transactions are read from `accounts[].transactions` and continue to flow through the existing raw-data pipeline (`BrokerRawTransaction` → FIFO aggregation → `Trade`).
- Add account-number matching to the Schwab import: when the target Trade Sensei Schwab `Account.account_number` is set and does not match any `accounts[].accountNumber` in the file, **abort the import with a descriptive error**. When it is unset, import the single account if the file contains exactly one, otherwise abort and list the available account numbers.
- Update the Schwab test fixture in `tests/test_data/schwab/` to the wrapped format and update the Schwab unit + integration tests accordingly.
- Add user documentation for the CLI tool (a `docs/` guide) and register it in a `tools/README.md` reference.

## Capabilities

### New Capabilities
- `schwab-positions-cli`: A command-line tool that authenticates to Schwab, resolves a single target account (auto-select when one, explicit `--account-id` when many, abort with the available account numbers otherwise), fetches positions and transactions, and writes them to a JSON file in the wrapped import schema — plus its user-facing documentation.

### Modified Capabilities
- `schwab-json-import`: The importer's accepted input format changes from a top-level transaction array to the wrapped `{accounts:[...]}` schema, and gains account-number matching/validation that can abort the import.

## Impact

- **Code**:
  - New: `tools/schwab_get_positions.py`, `docs/schwab-positions-tool.md`, `tools/README.md`.
  - Modified: `backend/app/utils/parsers/schwab_json.py` (accept wrapped format, extract transactions from `accounts[]`), `backend/app/services/import_service.py` and/or the Schwab import routes in `backend/app/api/v1/imports.py` (account-number matching + abort behaviour).
  - Possibly modified: `backend/app/utils/schwab_client.py` (add a positions fetch method if not present) — the CLI may instead be self-contained via `schwabdev`, decided in design.
- **APIs**: No new HTTP endpoints; the existing `POST /imports/upload` and `POST /imports/schwab-json` behaviour changes (input schema + new abort-on-mismatch error).
- **Test data / tests**: `tests/test_data/schwab/*.json` reformatted; `backend/tests/test_schwab_json_parser.py` and `backend/tests/test_schwab_json_import.py` updated; new tests for account-number matching and CLI account-resolution logic.
- **Dependencies**: The CLI relies on `schwabdev` + `python-dotenv` and Schwab OAuth env vars (`SCHWAB_APP_KEY`, `SCHWAB_APP_SECRET`, `SCHWAB_CALLBACK_URL`).
- **Non-breaking for consumers of the pipeline** (raw-transaction/aggregation layers unchanged); breaking only for the accepted Schwab file input shape.
