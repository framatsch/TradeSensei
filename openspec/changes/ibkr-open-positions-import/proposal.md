## Why

IBKR Flex Query XML reports contain `<OpenPosition>` elements that represent currently-held positions. The parser currently ignores these elements, so any position that was opened before the selected `from_date` (or outside the report window) is invisible to TradeSensei. This means the journal is always incomplete for active traders with multi-day or longer-term positions.

## What Changes

- The IBKR XML parser will read `<OpenPosition>` elements and convert each one into a `BrokerRawTransaction` + `LogicalExecution` pair (origin: `open_position`), representing the opening leg of a still-open trade.
- Each `<OpenPosition>` record carries a `transactionID` (or a deterministic fallback composite key) that matches the original `<Trade>` execution ID, allowing future closes to be linked to their open leg.
- When a position later closes and a `<Trade>` record appears in a subsequent import, the existing open-position execution is matched via `conid` + `executed_at` and the trade is closed normally — no duplicate open leg is created.
- The `Trade` projection for an open-position execution is stored as an open lot (no `closed_at`, `exit_price = None`).
- A new `origin` value `open_position` is added to `LogicalExecution` to distinguish these from regular imported executions.

## Capabilities

### New Capabilities

- `ibkr-open-position-ingestion`: Parse `<OpenPosition>` elements from IBKR Flex XML and persist them as open-lot execution legs, including deduplication against already-existing open lots.

### Modified Capabilities

- `raw-transaction-layer`: Add `open_position` as a valid `origin` value on `LogicalExecution`.
- `account-centric-broker-sync`: IBKR sync via Flex API now includes open positions from the report window.

## Impact

- `backend/app/utils/parsers/ibkr_xml.py` — new `<OpenPosition>` element parser in `parse_raw()`
- `backend/app/models/logical_execution.py` — new `EXECUTION_ORIGIN_OPEN_POSITION` constant
- `backend/app/services/import_service.py` — deduplication logic must handle open-position legs (skip if matching open lot already exists)
- `backend/tests/` — new unit tests for parser, integration test for full import cycle
- No API schema changes; no frontend changes required
