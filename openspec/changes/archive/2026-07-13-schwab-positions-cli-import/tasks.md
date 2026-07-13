## 1. Parser — wrapped format

- [x] 1.1 In `backend/app/utils/parsers/schwab_json.py`, change `parse_raw()` to require a top-level JSON **object** with an `accounts` array; raise `ImportParseError` (descriptive, wrapped-format-required) for a bare top-level array or a missing/invalid `accounts` key.
- [x] 1.2 Iterate `accounts[].transactions` and build raw records from each transaction's `transferItems` legs (reuse existing leg/commission/instruction/direction logic).
- [x] 1.3 Remove the `transactionItem` instrument branch and its commission short-circuit in `_extract_instrument()` / `_extract_commission()` (wrapped API always uses `transferItems`).
- [x] 1.4 Update `_parse_datetime()` to parse the `time` field including compact UTC offsets (e.g. `+0000`), keeping the result tz-aware and converted to UTC.
- [x] 1.5 Ensure `parse_raw()` still returns `(raw_records, [])` and still skips non-`TRADE`/invalid-status/unknown-instruction records with warnings.

## 2. Service — account-number matching

- [x] 2.1 Add an import-account-mismatch exception (e.g. `ImportAccountMismatchError`) in `backend/app/core/exceptions.py` (or reuse the closest existing 422-mapped error).
- [x] 2.2 In `backend/app/services/import_service.py`, before producing Schwab raw records, select the target file account entry: if `account.account_number` is set, pick the `accounts[]` entry with matching `accountNumber`; else use the sole entry when exactly one, otherwise raise the mismatch/ambiguity error.
- [x] 2.3 Raise the mismatch error with a message naming the configured account number vs. the file's account number(s); raise the ambiguity error listing the file's available `accountNumber` values.
- [x] 2.4 Ensure only the selected account's transactions flow into the raw-transaction pipeline; confirm IBKR and non-Schwab paths are untouched.
- [x] 2.5 When `account.account_number` is unset and the file has exactly one account, persist that `accountNumber` onto the `Account` row (normal update) so future imports auto-match.

## 3. API routes

- [x] 3.1 In `backend/app/api/v1/imports.py`, change the `POST /imports/schwab-json` body type from `list[dict]` to the wrapped object (`dict`) and update its `summary`/`description`/`responses` (add 422 for account mismatch/ambiguity).
- [x] 3.2 Map `ImportAccountMismatchError` (and ambiguity) to HTTP 422 in both `/imports/upload` and `/imports/schwab-json` handlers.
- [x] 3.3 Verify audit logging: only safe identifiers (`account_id`, `resource_id`) are logged; account numbers are not written to audit metadata.

## 4. CLI tool

- [x] 4.1 Create `tools/schwab_cli.py` from the `tmp/schwab_cli.py` prototype (schwabdev client, `.env` loading, token-exchange bugfix shim, redirect-URI auth helper, `rich` UI). Subcommands: `accounts`, `positions`, `transactions`, `refresh`.
- [x] 4.2 Each fetch subcommand takes `--account/-a` (Schwab account number), `--output/-o` (defaults to a `cache/` file next to the tool); `transactions` also takes `--start`/`--end` (default 90-day window).
- [x] 4.3 Implement account resolution (`_match_account`): exactly one linked account → auto-select; `--account` given → select matching, else exit non-zero listing available numbers; multiple linked accounts without `--account` → exit non-zero listing available numbers.
- [x] 4.4 The `positions` subcommand fetches positions + transactions only for the resolved account(s) and writes the wrapped payload `{fetchedAt, accounts:[{accountNumber, accountHash, positions, transactions}]}` — the format the importer consumes.
- [x] 4.5 Exit non-zero with a clear message when `SCHWAB_APP_KEY`/`SCHWAB_APP_SECRET` are missing.

## 5. Test data & tests

- [x] 5.1 Rewrite `tests/test_data/schwab/schwab_aggregation.json` into the wrapped format: one account entry, `transferItems`-shaped transactions with `time` fields, preserving the existing FIFO ground-truth (matched pairs / open lots).
- [x] 5.1a Populate the account entry's `positions[]` with open test positions (per the `Position` shape in `tmp/positions_schema.md`: `longQuantity`, `averagePrice`/`averageLongPrice`, `instrument` with `symbol`/`assetType`, `marketValue`, etc.) — one entry per symbol left open by the transactions' FIFO ground-truth, so the fixture mirrors a realistic Schwab payload with open holdings.
- [x] 5.1b In `backend/tests/test_schwab_json_import.py` (or the parser test), assert that the populated `positions[]` are ignored by the import pipeline — the trade ground-truth is unchanged whether `positions[]` is empty or filled — confirming only `transactions` drive the import (design Non-Goals).
- [x] 5.2 Update `backend/tests/test_schwab_json_parser.py` to the wrapped shape; add a test asserting a bare top-level array is rejected with `ImportParseError`; update datetime test to the `time`/`+0000` shape.
- [x] 5.3 Update `backend/tests/test_schwab_json_import.py` ground-truth + REST + parity + CSV-rejected tests to the wrapped fixture/body.
- [x] 5.4 Add tests for account-number matching: match (imports), mismatch with configured number (422), unset + single account (imports), unset + multiple accounts (422 listing numbers).
- [x] 5.5 Add unit tests for the CLI account-resolution logic (single auto-select, `--account-id` match/mismatch, multiple-without-id abort) with `linked_accounts()` mocked.

## 6. Documentation

- [x] 6.1 Add `docs/schwab-positions-tool.md`: required env vars, how to run each subcommand, `--account`/`--start`/`--end`/`--output`, output location/format, the "widen `--start` to include open positions' opening trades" note, and the end-to-end "download then import into Trade Sensei" workflow.
- [x] 6.2 Add or update `tools/README.md` to list `schwab_cli.py` with a one-line description and a link to `docs/schwab-positions-tool.md`.

## 7. Verification

- [x] 7.1 Run `lint-check` (ruff + `mypy --strict`) on the backend and fix any errors.
- [x] 7.2 Run `unit-test` (pytest) for the Schwab parser + import + new matching/CLI tests; confirm green.
- [x] 7.3 Manually run `python tools/schwab_cli.py --help` and `python tools/schwab_cli.py positions --help`; confirm the wrapped output file is produced (or mock/dry-run if no live Schwab creds), then import it via the endpoint to confirm end-to-end flow.
