## Why

The Schwab wrapped import file (`{fetchedAt, dateRange, accounts:[{..., positions, transactions}]}`) carries a `positions[]` array of currently-held holdings, but the Schwab importer only turns `transactions` into trades — `positions[]` is written to the file and ignored (`schwab-positions-cli-import` Non-Goal). So a Schwab position opened before the transaction window is invisible to Trade Sensei, exactly as it was for IBKR before its adapter.

The broker-neutral contract for open-position ingestion is `open-position-seeding`. This change is the **Schwab adapter**: it turns each `positions[]` entry into a contract-flagged open-position raw record. Unlike IBKR, Schwab `positions[]` has no per-lot id and no open date, so this adapter uses the contract's deterministic-fallback + approximate-reconciliation path.

> **Depends on:** `open-position-seeding` (contract). This change MUST NOT re-declare the `open_position` origin, the CHECK-constraint widening, or the `is_open_position` flag. It only implements the Schwab-specific mapping into the contract, and relies on the contract's supersede guard for reconciliation (Schwab has no shared id).

## What Changes

- The Schwab JSON parser reads each `accounts[].positions[]` entry and emits one `BrokerRawTransactionCreate` per open holding, flagged `is_open_position = true`.
- Schwab-specific keys satisfy the contract's determinism requirement despite no natural id/date:
  - raw `id = "schwab:openpos:{accountNumber}:{symbol}:{longQuantity}"` (deterministic → idempotent re-import; for options `{symbol}` is the full OCC option symbol).
  - `executed_at` = the file's `dateRange.start` (ordering-safe approximate open time — guaranteed to precede any close in the same window; see design D2).
  - price from `averageLongPrice` (fallback `averagePrice`); quantity from `longQuantity`; direction LONG (short holdings handled symmetrically via `shortQuantity` if present).
- Both `EQUITY` (multiplier 1) and `OPTION` (multiplier 100, OCC symbol as-is) positions are seeded; other asset types (mutual fund, fixed income, cash, currency, futures) are skipped with a warning.
- Reconciliation for Schwab is **approximate** and relies on the contract's snapshot-replace rule: position snapshots are the source of truth for the account's open lots, so a re-import replaces stale/quantity-changed snapshot legs, and a later real opening execution for the same instrument `(symbol, conid=None, asset_class)` supersedes the snapshot leg.

## Capabilities

### New Capabilities

- `schwab-open-position-ingestion`: Parse `accounts[].positions[]` from the Schwab wrapped file into contract-compliant open-position raw records (Schwab adapter for `open-position-seeding`). This is additive to `schwab-json-import` (which continues to drive trades from `transactions`); the `positions[]` array — previously written-but-ignored — is now also seeded as open lots.

## Impact

- **Code**:
  - `backend/app/utils/parsers/schwab_json.py` — new `positions[]` handling in `parse_raw()`, emitting `is_open_position = true` records alongside transaction-derived records.
  - No model/constraint/service changes beyond consuming the contract.
  - `backend/tests/` — Schwab positions parser tests + integration tests for seed / idempotency / approximate reconciliation.
- **APIs**: No new endpoints; no schema changes (same wrapped body).
- **Depends on**: `open-position-seeding` (flag, origin, constraint, service branch, and the no-shared-id supersede guard). Naturally sequenced after `schwab-positions-cli-import` (which establishes the wrapped format) — though it only needs the wrapped `positions[]` shape, not the CLI itself.
