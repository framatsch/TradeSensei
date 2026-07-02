## 1. DB Model — Add open_position origin

- [ ] 1.1 Add `EXECUTION_ORIGIN_OPEN_POSITION = "open_position"` constant to `backend/app/models/logical_execution.py` and include it in `VALID_ORIGINS`
- [ ] 1.2 Create Alembic migration to widen the CHECK constraint on `logical_executions.origin` to include `"open_position"`
- [ ] 1.3 Verify migration applies cleanly (`alembic upgrade head`) and rolls back cleanly (`alembic downgrade -1`)

## 2. Parser — OpenPosition ingestion

- [ ] 2.1 Add `_parse_open_position_element_raw()` method to `IBKRXMLParser` in `backend/app/utils/parsers/ibkr_xml.py` that converts an `<OpenPosition>` element to a `BrokerRawTransactionCreate`
- [ ] 2.2 Set `executed_at` from `openDate` attribute; compute `price` as `abs(costBasis) / (abs(position) * multiplier)`; set `pnl = None`; use `transactionID` for the raw ID (with deterministic composite fallback)
- [ ] 2.3 Skip elements with `assetCategory = "CASH"` silently; skip elements missing `symbol` with a warning
- [ ] 2.4 Call `_parse_open_position_element_raw()` inside `parse_raw()` after processing `<Trade>` and `<Execution>` elements (loop over `root.findall(".//OpenPosition")`)

## 3. Service — LogicalExecution origin for open positions

- [ ] 3.1 In `backend/app/services/logical_execution_service.py` (or wherever `LogicalExecution` records are created from raw transactions), detect `BrokerRawTransaction` records sourced from `<OpenPosition>` and set `origin = EXECUTION_ORIGIN_OPEN_POSITION`
- [ ] 3.2 Confirm deduplication: `bulk_upsert` in `BrokerRawTransactionRepository` already skips existing IDs — verify no additional logic is needed for the open-position case
- [ ] 3.3 Ensure `import_service.py` does not soft-delete or skip `open_position` LogicalExecutions during re-aggregation (they should be treated as regular opening legs by the FIFO aggregator)

## 4. Unit Tests — Parser

- [ ] 4.1 Write a unit test in `backend/tests/` that provides a minimal Flex XML with `<OpenPosition>` elements and asserts the parser emits the correct `BrokerRawTransactionCreate` records (symbol, direction, quantity, price, `executed_at`, `pnl=None`, correct `id` format)
- [ ] 4.2 Write a unit test for the composite-key fallback when `transactionID` is absent
- [ ] 4.3 Write a unit test that verifies CASH `<OpenPosition>` elements are skipped
- [ ] 4.4 Write a unit test that verifies a missing-symbol `<OpenPosition>` appends a warning and returns `None`

## 5. Unit Tests — Origin constant and VALID_ORIGINS

- [ ] 5.1 Add a test asserting `"open_position"` is in `VALID_ORIGINS`
- [ ] 5.2 Add a test asserting `LogicalExecution` can be constructed with `origin = EXECUTION_ORIGIN_OPEN_POSITION` without DB constraint errors (use a mock or in-memory approach)

## 6. Integration Test — Full open-position import cycle

- [ ] 6.1 Write an integration test that runs a full Flex XML import (via `ImportService.import_file`) with a fixture containing both `<OpenPosition>` and `<Trade>` elements; assert the open position creates an open-lot `Trade` and the closing `<Trade>` closes it correctly
- [ ] 6.2 Write an integration test that runs the same XML twice and asserts no duplicate `BrokerRawTransaction` or `LogicalExecution` records are created on the second run

## 7. Verification

- [ ] 7.1 Run `rtk pytest backend/tests/ -m "not integration" -q` — all unit tests pass
- [ ] 7.2 Run `rtk lint` and `rtk tsc` (mypy) — zero new errors
