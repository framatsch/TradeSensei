## Why

IBKR Flex Query XML reports contain `<OpenPosition>` elements representing currently-held positions. The parser ignores them today, so any position opened before the selected `from_date` (or outside the report window) is invisible to Trade Sensei — the journal is always incomplete for active traders with multi-day or longer-term positions.

The broker-neutral domain contract for turning a position snapshot into an open lot is defined by the `open-position-seeding` capability (`open_position` origin, `is_open_position` flag, reconciliation semantics, idempotency). This change is the **IBKR adapter** for that contract: it supplies only the IBKR-specific parse step and reuses the shared domain layer unchanged.

> **Depends on:** `open-position-seeding` (contract). This change MUST NOT re-declare the `open_position` origin, the `logical_executions.origin` CHECK-constraint widening, or the `is_open_position` flag — those are owned by the contract. It only implements the IBKR-specific mapping into that contract.

## What Changes

- The IBKR XML parser reads `<OpenPosition>` elements and emits one `BrokerRawTransactionCreate` per position, flagged `is_open_position = true` (the contract's neutral flag), so the shared layer maps it to `LogicalExecution(origin = "open_position", pnl = None)`.
- IBKR-specific keys satisfy the contract's determinism requirement: raw `id = "ibkr:{transactionID}"` (matches the original opening `<Trade>` id, enabling exact reconciliation), `executed_at` from `openDate`, price from `abs(costBasis) / (abs(position) * multiplier)`.
- `<OpenPosition>` with `assetCategory = "CASH"` are skipped silently; those missing `symbol` are skipped with a warning.
- IBKR API sync (Flex) now includes open positions from the report window, with no duplicates on re-sync (idempotency via the contract's shared-id path).

## Capabilities

### New Capabilities

- `ibkr-open-position-ingestion`: Parse `<OpenPosition>` elements from IBKR Flex XML into contract-compliant open-position raw records (IBKR adapter for `open-position-seeding`).

### Modified Capabilities

- `account-centric-broker-sync`: IBKR API sync includes `<OpenPosition>` elements as open-lot legs, deduplicated on re-sync.

## Impact

- **Code**:
  - `backend/app/utils/parsers/ibkr_xml.py` — new `<OpenPosition>` element parser in `parse_raw()`, setting `is_open_position = true`.
  - No changes to `LogicalExecution` model origin, the CHECK constraint, or `LogicalExecutionService` beyond what the contract provides (this change consumes them).
  - `backend/tests/` — IBKR parser unit tests + an integration test for the full IBKR open→close cycle.
- **APIs**: No new endpoints; no schema changes.
- **Depends on**: `open-position-seeding` must land first (or together) so the `is_open_position` flag, `open_position` origin, and reconciliation guard exist.
