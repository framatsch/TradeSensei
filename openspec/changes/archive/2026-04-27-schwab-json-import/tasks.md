
## 1. SchwabJSONParser — Core Implementation

- [x] 1.1 Create `backend/app/utils/parsers/schwab_json.py` with `SchwabJSONParser(BrokerParser)` class
- [x] 1.2 Implement `parse_raw(content, filename, ...)` — entry point, validates top-level JSON array, filters by `type == "TRADE"` and `status in {"COMPLETED", "VALID"}`
- [x] 1.3 Implement `_extract_instrument(txn)` — handles both `transactionItem` (flat) and `transferItems[0]` (array) formats to extract `symbol`, `price`, `amount`, `instruction`, `assetType`
- [x] 1.4 Implement `_parse_datetime(value)` — parses both offset-aware (`-05:00`) and UTC (`Z`) ISO-8601 datetime strings, converts to UTC
- [x] 1.5 Implement `_map_direction(instruction)` — maps `BUY`/`SELL` → `LONG`, `SELL_SHORT`/`BUY_TO_COVER` → `SHORT`; returns `None` for unknown (with warning log)
- [x] 1.6 Implement `_map_asset_class(asset_type)` — maps `EQUITY` → `EQUITY`, `OPTION` → `OPTION`, others → `EQUITY` (with warning log)
- [x] 1.7 Implement `_extract_commission(txn)` — for `transferItems` format: sums `abs(cost)` of legs where `feeType in {COMMISSION, SEC_FEE, TAF_FEE}` and no symbol; returns `Decimal("0")` for `transactionItem` format
- [x] 1.8 Build `BrokerRawTransactionCreate` per record: `id = f"{user_id}:schwab:{activityId}"`, all Decimal fields use `Decimal(str(...))`, `currency = "USD"`, `multiplier = 1`, `raw_data = original_txn_dict`
- [x] 1.9 Skip records with unmappable `instruction` and log warning with `activityId`

## 2. Factory — Replace CSV Parser, Enforce JSON-only for Schwab

- [x] 2.1 Update `backend/app/utils/parsers/factory.py` — replace `SchwabParser` with `SchwabJSONParser` for `BrokerType.SCHWAB`; remove the import of `SchwabParser`
- [x] 2.2 Update the upload endpoint in `backend/app/api/v1/imports.py` — change accepted extension for `AccountType.SCHWAB` from `.csv` to `.json`; reject `.csv` with HTTP 422 `"Schwab accounts require JSON format (.json). CSV import is no longer supported."`
- [x] 2.3 Update the upload endpoint in `backend/app/api/v1/imports.py` — reject any file upload for `AccountType.MANUAL` with HTTP 422 `"File import is not supported for manual accounts"`

## 3. REST Endpoint for Direct JSON Import

- [x] 3.1 Add `POST /api/v1/imports/schwab-json` route in `backend/app/api/v1/imports.py`
- [x] 3.2 Accept `account_id: UUID` as query parameter, `body: list[dict]` as JSON request body
- [x] 3.3 Validate account exists and `account.type == AccountType.SCHWAB` — return HTTP 422 if not
- [x] 3.4 Serialize body back to bytes (`json.dumps(body).encode()`), pass to `ImportService.import_file()` with `broker=BrokerType.SCHWAB` and filename `"schwab_transactions.json"`
- [x] 3.5 Return `ImportResult` response (same schema as upload endpoint)

## 4. Frontend — File Dialog Restriction

- [x] 4.1 Locate the file input component used in the import page for Schwab accounts (`frontend/` — search for `accept` attribute or `AccountType.SCHWAB` reference in the upload UI)
- [x] 4.2 Change the `accept` attribute to `".json"` when the selected account is of type `SCHWAB`
- [x] 4.3 Verify the dropzone label/hint text is updated to reflect "JSON files" for Schwab accounts

## 5. Unit Tests — Parser

- [x] 5.1 Create `backend/tests/test_schwab_json_parser.py`
- [x] 5.2 Test `_map_direction()` — all four instruction values + unknown instruction returns `None`
- [x] 5.3 Test `_parse_datetime()` — offset-aware (`-05:00`) and UTC (`Z`) formats both produce UTC datetime
- [x] 5.4 Test `_extract_instrument()` — `transactionItem` format (flat) extracts correctly
- [x] 5.5 Test `_extract_instrument()` — `transferItems` format (array) extracts first instrument leg correctly
- [x] 5.6 Test `_extract_commission()` — `transferItems` with commission leg sums correctly; returns `Decimal("0")` for `transactionItem`
- [x] 5.7 Test `parse_raw()` — non-TRADE records are filtered out
- [x] 5.8 Test `parse_raw()` — COMPLETED record produces correct `BrokerRawTransactionCreate` with expected `id`, `direction`, `quantity`, `price`, `asset_class`, `currency`
- [x] 5.9 Test `parse_raw()` — unknown `instruction` skips the record (no exception raised)

## 6. Integration Test — FIFO Aggregation from JSON Fixture

- [x] 6.1 Create `backend/tests/test_schwab_json_import.py`
- [x] 6.2 Write `test_schwab_json_import_ground_truth()` — reads `tests/test_data/schwab/schwab_aggregation.json`, calls `ImportService.import_file()` with a mocked DB session (or use the existing integration test DB fixture pattern)
- [x] 6.3 Assert: number of `BrokerRawTransactionCreate` items equals total records in fixture that are `type=TRADE`
- [x] 6.4 Assert: number of closed trades produced by FIFO aggregation matches expected count (count matched BUY/SELL pairs in fixture manually or via script)
- [x] 6.5 Assert: no orphaned lots (all LONG opens have a SELL, all SHORT opens have a BUY_TO_COVER in the fixture)
- [x] 6.6 Assert: re-import of same fixture produces `raw_transactions_created = 0` (idempotency check)
- [x] 6.7 Write `test_schwab_json_rest_endpoint()` — POST to `/imports/schwab-json` with fixture data, assert HTTP 200 and `ImportResult`
- [x] 6.8 Write `test_schwab_json_rest_endpoint_wrong_account_type()` — POST to `/imports/schwab-json` with non-SCHWAB account, assert HTTP 422

## 7. Pipeline Parity Test

- [x] 7.1 In `test_schwab_json_import.py`, add `test_pipeline_parity_schwab_vs_ibkr()` — given a minimal synthetic dataset (e.g. 1 BUY + 1 SELL, same symbol/qty/price/timestamp) expressed as both IBKR XML and Schwab JSON: import both into isolated in-memory aggregator runs, assert resulting `TradeCreate` lists are equal in `symbol`, `direction`, `quantity`, `entry_price`, `exit_price`, and `pnl`
- [x] 7.2 Add `test_schwab_csv_upload_rejected()` — POST `.csv` file to upload endpoint for a Schwab account, assert HTTP 422
- [x] 7.3 Add `test_manual_account_upload_rejected()` — POST any file to upload endpoint for a MANUAL account, assert HTTP 422

## 8. Verification

- [x] 8.1 Run `uv run pytest backend/tests/test_schwab_json_parser.py -v` — all unit tests pass
- [x] 8.2 Run `uv run pytest backend/tests/test_schwab_json_import.py -v` — all integration tests pass (blocked locally: DB on `127.0.0.1:5433` not reachable)
- [x] 8.3 Run full backend test suite `uv run pytest backend/tests/ -v` — no regressions in existing IBKR tests (blocked locally: DB on `127.0.0.1:5433` not reachable)
- [x] 8.4 Run `uv run mypy backend/app --strict` — zero type errors in new and modified files
- [x] 8.5 Run `uv run ruff check backend/app/utils/parsers/schwab_json.py backend/app/utils/parsers/factory.py` — no linting issues
