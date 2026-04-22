## Why

The existing Schwab import pipeline only supports CSV files, which use the legacy `parse()` path without raw transaction tracking. Schwab's official Individual Trader API delivers transaction data in JSON format (`transferItems`-based schema), which is richer, more structured, and supports equities, options, and multi-leg combos. Adopting JSON import (both file upload and REST endpoint) enables a raw-data pipeline (with `BrokerRawTransaction` idempotency) consistent with the IBKR flow, eliminating re-import duplication and enabling proper audit trails.

## What Changes

- **New**: `SchwabJSONParser` — parses the Schwab Transactions JSON format (`activityId`, `transactionItem`, `netAmount`) into `BrokerRawTransactionCreate` objects via `parse_raw()`, enabling the raw-data pipeline
- **New**: REST endpoint `POST /api/v1/imports/schwab-json` — accepts a JSON array body (the Schwab API transaction payload) directly, without file upload
- **Modified**: File upload endpoint (`POST /api/v1/imports/upload`) — Schwab accounts now accept `.json` files in addition to/replacing `.csv`; file dialog restricted to `.json` only for Schwab
- **Modified**: Frontend import page — file input `accept` for Schwab accounts changes from `.csv` to `.json`
- **New**: `SchwabJSONParser.parse_raw()` maps Schwab `instruction` field (`BUY`, `SELL`, `SELL_SHORT`, `BUY_TO_COVER`) to `direction` and derives `asset_class` from `instrument.assetType`
- **New**: Deduplication via BRT `id` = `"{user_id}:schwab:{activityId}"` — idempotent across re-imports
- **New**: Test data: `tests/test_data/schwab/schwab_aggregation.json` used as ground-truth fixture
- **New**: Integration test verifying FIFO aggregation from JSON fixture matches expected trade count and P&L

## Capabilities

### New Capabilities

- `schwab-json-import`: Full import pipeline for Schwab Transactions JSON format — file upload (.json), REST endpoint, raw-data pipeline with BRT idempotency, FIFO aggregation, and integration tests

### Modified Capabilities

- `trade-import`: Schwab accounts now accept `.json` upload (not `.csv`); the import dashboard file input `accept` attribute changes for Schwab accounts

## Impact

- **Backend**: New parser file `backend/app/utils/parsers/schwab_json.py`; factory updated to route Schwab to new parser for `.json` files; new API route in `backend/app/api/v1/imports.py`
- **Frontend**: `frontend/` import page file input `accept` attribute for Schwab changed from `.csv` to `.json`
- **Tests**: New `backend/tests/test_schwab_json_import.py` with unit + integration tests
- **No DB migrations needed** — BrokerRawTransaction and Trade models are unchanged
- **No breaking changes** — existing Schwab CSV import continues to work; JSON is additive
