## 1. Rename the import entry point

- [x] 1.1 Rename `ImportService.import_file()` to `ImportService.import_trades()` (`services/import_service.py:164`)
- [x] 1.2 Update all call sites in `app/`: `api/v1/imports.py` (2 calls), `services/broker_service.py` (1 call), and the internal call in `import_service.py`
- [x] 1.3 Update the audit `path=` label (`import_service.py:1863`) and the docstring reference in `core/constants.py:259`
- [x] 1.4 Update all test call sites and mock patch targets
- [x] 1.5 Keep the `filename` parameter and `ImportResult.filename` field; update their descriptions to state the value is a source label that is synthetic for non-file paths (`flex_query_{query_id}.xml`, `schwab_transactions_sync.json`). **Do not rename the response field** — it is part of the public API contract
- [x] 1.6 Confirm no `import_file` reference remains anywhere in `backend/`

## 2. Reduce FlexImportService to an API client

- [x] 2.1 Extract the Flex fetch workflow into a public method on `FlexImportService` that returns the raw XML bytes (reusing `_fetch_flex_xml`, `_send_request`, `_poll_report` unchanged)
- [x] 2.2 Remove trade parsing, FIFO aggregation, `find_duplicate` deduplication, `manually_edited_keys` skipping, and all repository writes from `flex_import_service.py`
- [x] 2.3 Remove the now-unused `IBKRXMLParser`, `TradeRepository`, and `PortfolioRepository` dependencies from `FlexImportService`; keep account-ownership validation only if a caller still relies on it, otherwise move it to the caller
- [x] 2.4 Update the module docstring to state that this class only talks to the IBKR Flex Web Service and never persists

## 3. Route both IBKR entry points through ImportService

- [x] 3.1 Rewrite `BrokerService._sync_ibkr` to fetch the XML then call `ImportService.import_trades(content=xml, filename=f"flex_query_{query_id}.xml", broker=BrokerType.IBKR, portfolio_id=..., account_id=account.id, user_id=account.user_id, overwrite_manually_edited=...)`, mirroring `_sync_schwab` (`broker_service.py:605-614`)
- [x] 3.2 Map the returned `ImportResult` onto `BrokerSyncResult` including `trades_protected_reconciled` and `trades_protected_skipped`, matching the `_sync_schwab` mapping
- [x] 3.3 Update the `POST /portfolios/{id}/imports/flex` handler (`api/v1/imports.py:614`) to fetch via `FlexImportService` and import via `ImportService`, preserving the existing request contract and error mapping (400 / 404 / 429 / 503)
- [x] 3.4 Preserve account-ownership validation for the endpoint's optional `account_id`
- [x] 3.5 Verify `get_parser(BrokerType.IBKR)` resolves to `IBKRXMLParser` so the fetched XML needs no translation

## 4. Documentation and architecture rule

- [x] 4.1 Add an "Ingestion Paths" rule to `AGENTS.md` §5 Non-Negotiable Rules: every broker ingestion path (file upload, scheduled sync, API pull) MUST terminate in `ImportService.import_trades()`; broker clients may fetch remote payloads but MUST NOT parse, aggregate, deduplicate, or persist; no ingestion path may create a `Trade` directly
- [x] 4.2 Note in `AGENTS.md` that `BrokerService._sync_schwab` is the reference implementation of this pattern
- [x] 4.3 Update `docs/api-usage.md` to state that Flex import and IBKR file upload are behaviourally identical and both populate raw transactions and executions
- [x] 4.4 Append the change to the `[Unreleased]` section of `CHANGELOG.md`

## 5. Backend tests

- [x] 5.1 `POST /imports/flex` delegates to `ImportService.import_trades` with `BrokerType.IBKR` and the fetched XML
- [x] 5.2 `FlexImportService` performs no repository writes (assert no trade/execution rows are created by the client alone)
- [x] 5.3 An IBKR sync creates `BrokerRawTransaction` and `LogicalExecution` rows and links executions to their trades
- [x] 5.4 Importing the same Flex report twice is a no-op (raw `source_id` idempotency plus the zero-insert guard)
- [x] 5.5 The same report delivered by file upload and by sync produces identical trades, executions, and raw transactions
- [x] 5.6 A metadata-protected trade survives an IBKR sync with structural fields and leg links unchanged
- [x] 5.7 No sentinel orphan trade is created via the sync path for a contract held by a protected trade
- [x] 5.8 No trade created by any ingestion path lacks linked executions (reproduces the leg-less phantom-trade defect)
- [x] 5.9 IBKR `BrokerSyncResult` surfaces the protection counters
- [x] 5.10 Regression: `BrokerService._sync_schwab` still delegates to `ImportService.import_trades` (locks in the currently-correct Schwab path)
- [x] 5.11 Remove or rewrite the obsolete `FlexImportService` tests that asserted parsing, dedup, or persistence behaviour

## 6. Verification

- [x] 6.1 Run the `lint-check` skill (ruff + `mypy --strict`) with zero errors
- [x] 6.2 Run the `unit-test` skill and confirm all backend tests pass
- [x] 6.3 Dry-run an IBKR sync against a restored production snapshot and confirm: executions are created and linked, protected trades' `updated_at` and leg links are unchanged, and no new leg-less or sentinel trade appears
- [x] 6.4 Confirm a second consecutive sync reports zero created trades and triggers no projection rebuild
