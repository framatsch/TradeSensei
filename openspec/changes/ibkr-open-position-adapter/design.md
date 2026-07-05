## Context

`IBKRXMLParser.parse_raw()` currently processes `<Trade>` and `<Execution>` elements. `<OpenPosition>` elements are read only to build a validation set of open conids — never converted into raw records. This change makes the parser emit contract-compliant open-position raw records.

The domain semantics (open lot, `origin = "open_position"`, `pnl = None`, idempotency, reconciliation) are **not** re-specified here — they belong to `open-position-seeding`. This change is a thin adapter: parse IBKR XML → produce `BrokerRawTransactionCreate(is_open_position=True, ...)` with IBKR-specific keys.

## Goals / Non-Goals

**Goals:**
- Parse `<OpenPosition>` in `parse_raw()` and emit one raw record per position, flagged `is_open_position = true`.
- Satisfy the contract's determinism requirement with IBKR-native keys (`transactionID`, `openDate`).
- IBKR API sync includes open positions; re-sync creates no duplicates.

**Non-Goals:**
- Defining `open_position` origin, the CHECK constraint, or the `is_open_position` flag (owned by `open-position-seeding`).
- Changing the FIFO aggregator or the reconciliation guard (owned by the contract).
- Schwab or other brokers.
- Detecting when an open position transitions to closed (happens naturally when the closing `<Trade>` arrives).

## Decisions

### D1: Reuse the contract's raw-record path; supply only IBKR keys

`_parse_open_position_element_raw()` converts an `<OpenPosition>` element to a `BrokerRawTransactionCreate` with:
- `is_open_position = True` (contract flag)
- `id = "ibkr:{transactionID}"` — same scheme as `<Trade>`, so a later real opening `<Trade>` collapses via `bulk_upsert` (contract's exact-reconciliation path). Fallback when `transactionID` is absent: deterministic composite `ibkr:{symbol}:{yyyymmddHHMMSS}:{quantity}` (same fallback shape as `<Trade>`).
- `executed_at` from `openDate` (UTC) — matches what the eventual `<Trade>` opening leg carries, so FIFO can pair them.
- `price = abs(costBasis) / (abs(position) * multiplier)`.

Rationale: because IBKR provides both a stable id and an open date, the IBKR adapter hits the contract's **exact** reconciliation path (D4/path 1 of `open-position-seeding`) — no supersede guard needed for IBKR.

### D2: Skip rules

- `assetCategory = "CASH"` → skip silently (not a tradable open lot).
- Missing `symbol` → skip with a warning appended to `IBKRXMLParser.warnings`.

### D3: No model/service/migration work here

The `open_position` origin, `VALID_ORIGINS` entry, CHECK-constraint migration, `is_open_position` schema field, the `create_from_raw()` branch, and the reconciliation guard are all delivered by `open-position-seeding`. This change asserts they exist (dependency) and exercises them via IBKR fixtures.

## Risks / Trade-offs

- **[Risk] `transactionID` absent in some Flex configs** → composite-key fallback (D1), same as `<Trade>`.
- **[Risk] Same position present as both `<Trade>` opening leg and `<OpenPosition>`** → shared `id` means `bulk_upsert` collapses them (contract exact path). No duplicate open leg.
- **[Risk] Contract not yet landed** → this change cannot compile/pass (no `is_open_position` field). Mitigation: sequence `open-position-seeding` first (or ship together).

## Migration Plan

1. Land `open-position-seeding` (flag, origin, constraint, service branch, guard).
2. Land this adapter (parser + tests).
3. Next IBKR sync/file import picks up `<OpenPosition>` automatically.

Rollback: revert the parser change; the contract layer is untouched and remains valid for other adapters.

## Open Questions

- None. IBKR keys and skip rules are settled; all domain semantics defer to the contract.
