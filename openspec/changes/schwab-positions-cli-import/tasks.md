## 1. Parser — wrapped format

- [ ] 1.1 In `backend/app/utils/parsers/schwab_json.py`, change `parse_raw()` to require a top-level JSON **object** with an `accounts` array; raise `ImportParseError` (descriptive, wrapped-format-required) for a bare top-level array or a missing/invalid `accounts` key.
- [ ] 1.2 Iterate `accounts[].transactions` and build raw records from each transaction's `transferItems` legs (reuse existing leg/commission/instruction/direction logic).
- [ ] 1.3 Remove the `transactionItem` instrument branch and its commission short-circuit in `_extract_instrument()` / `_extract_commission()` (wrapped API always uses `transferItems`).
- [ ] 1.4 Update `_parse_datetime()` to parse the `time` field including compact UTC offsets (e.g. `+0000`), keeping the result tz-aware and converted to UTC.
- [ ] 1.5 Ensure `parse_raw()` still returns `(raw_records, [])` and still skips non-`TRADE`/invalid-status/unknown-instruction records with warnings.

## 2. Service — account-number matching

- [ ] 2.1 Add an import-account-mismatch exception (e.g. `ImportAccountMismatchError`) in `backend/app/core/exceptions.py` (or reuse the closest existing 422-mapped error).
- [ ] 2.2 In `backend/app/services/import_service.py`, before producing Schwab raw records, select the target file account entry: if `account.account_number` is set, pick the `accounts[]` entry with matching `accountNumber`; else use the sole entry when exactly one, otherwise raise the mismatch/ambiguity error.
- [ ] 2.3 Raise the mismatch error with a message naming the configured account number vs. the file's account number(s); raise the ambiguity error listing the file's available `accountNumber` values.
- [ ] 2.4 Ensure only the selected account's transactions flow into the raw-transaction pipeline; confirm IBKR and non-Schwab paths are untouched.
- [ ] 2.5 When `account.account_number` is unset and the file has exactly one account, persist that `accountNumber` onto the `Account` row (normal update) so future imports auto-match.

## 3. API routes

- [ ] 3.1 In `backend/app/api/v1/imports.py`, change the `POST /imports/schwab-json` body type from `list[dict]` to the wrapped object (`dict`) and update its `summary`/`description`/`responses` (add 422 for account mismatch/ambiguity).
- [ ] 3.2 Map `ImportAccountMismatchError` (and ambiguity) to HTTP 422 in both `/imports/upload` and `/imports/schwab-json` handlers.
- [ ] 3.3 Verify audit logging: only safe identifiers (`account_id`, `resource_id`) are logged; account numbers are not written to audit metadata.

## 4. CLI tool

- [ ] 4.1 Create `tools/schwab_get_positions.py` from the `tmp/schwab_get_positions.py` prototype (schwabdev client, `.env` loading, token-exchange bugfix shim, redirect-URI auth helper).
- [ ] 4.2 Add `--account-id` (Schwab account number), plus existing `--start`/`--end`; add `--output` (default `./tmp/positions.json`).
- [ ] 4.3 Implement account resolution: exactly one linked account → auto-select; `--account-id` given → select matching, else exit non-zero listing available numbers; multiple linked accounts without `--account-id` → exit non-zero listing available numbers.
- [ ] 4.4 Fetch positions + transactions only for the resolved account and write the wrapped payload `{fetchedAt, dateRange, accounts:[{accountNumber, accountHash, positions, transactions}]}` (single account entry).
- [ ] 4.5 Exit non-zero with a clear message when `SCHWAB_APP_KEY`/`SCHWAB_APP_SECRET` are missing.

## 5. Test data & tests

- [ ] 5.1 Rewrite `tests/test_data/schwab/schwab_aggregation.json` into the wrapped format: one account entry, `transferItems`-shaped transactions with `time` fields, preserving the existing FIFO ground-truth (matched pairs / open lots).
- [ ] 5.1a Populate the account entry's `positions[]` with open test positions (per the `Position` shape in `tmp/positions_schema.md`: `longQuantity`, `averagePrice`/`averageLongPrice`, `instrument` with `symbol`/`assetType`, `marketValue`, etc.) — one entry per symbol left open by the transactions' FIFO ground-truth, so the fixture mirrors a realistic Schwab payload with open holdings.
- [ ] 5.1b In `backend/tests/test_schwab_json_import.py` (or the parser test), assert that the populated `positions[]` are ignored by the import pipeline — the trade ground-truth is unchanged whether `positions[]` is empty or filled — confirming only `transactions` drive the import (design Non-Goals).
- [ ] 5.2 Update `backend/tests/test_schwab_json_parser.py` to the wrapped shape; add a test asserting a bare top-level array is rejected with `ImportParseError`; update datetime test to the `time`/`+0000` shape.
- [ ] 5.3 Update `backend/tests/test_schwab_json_import.py` ground-truth + REST + parity + CSV-rejected tests to the wrapped fixture/body.
- [ ] 5.4 Add tests for account-number matching: match (imports), mismatch with configured number (422), unset + single account (imports), unset + multiple accounts (422 listing numbers).
- [ ] 5.5 Add unit tests for the CLI account-resolution logic (single auto-select, `--account-id` match/mismatch, multiple-without-id abort) with `linked_accounts()` mocked.

## 6. Documentation

- [ ] 6.1 Add `docs/schwab-positions-tool.md`: required env vars, how to run, `--account-id`/`--start`/`--end`/`--output`, output location/format, and the end-to-end "download then import into Trade Sensei" workflow.
- [ ] 6.2 Add or update `tools/README.md` to list `schwab_get_positions.py` with a one-line description and a link to `docs/schwab-positions-tool.md`.

## 7. Verification

- [ ] 7.1 Run `lint-check` (ruff + `mypy --strict`) on the backend and fix any errors.
- [ ] 7.2 Run `unit-test` (pytest) for the Schwab parser + import + new matching/CLI tests; confirm green.
- [ ] 7.3 Manually run `python tools/schwab_get_positions.py --help` and confirm the wrapped output file is produced (or mock/dry-run if no live Schwab creds), then import it via the endpoint to confirm end-to-end flow.
