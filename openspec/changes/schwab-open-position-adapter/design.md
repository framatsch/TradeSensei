## Context

After `schwab-positions-cli-import`, the Schwab importer accepts the wrapped file and drives trades from `accounts[].transactions`. Each account also carries `positions[]` — a snapshot of open holdings (`longQuantity`, `averagePrice`/`averageLongPrice`, `marketValue`, `instrument.symbol`, …; see `tmp/positions_schema.md`). Those are currently written but never imported.

This change is the Schwab adapter for `open-position-seeding`. The domain semantics (open lot, `origin = "open_position"`, `pnl = None`, idempotency, reconciliation guard) live in the contract; this change only maps `positions[]` → contract-flagged raw records.

The defining Schwab difference vs. IBKR: **no per-lot id, no open date.** IBKR gets exact reconciliation for free via a shared `transactionID`. Schwab cannot, so it uses the contract's deterministic-fallback id and the **no-shared-id supersede guard** for reconciliation.

## Goals / Non-Goals

**Goals:**
- Map each `positions[]` entry to one `BrokerRawTransactionCreate(is_open_position=True, ...)` with a deterministic id and UTC `executed_at`.
- Idempotent re-import (same file → same ids → no-ops).
- Correct reconciliation via the contract guard when a later real execution opens/closes the same position.

**Non-Goals:**
- Defining the contract (origin, flag, constraint, guard) — owned by `open-position-seeding`.
- Importing `positions[]` for live market-value / unrealised-P&L display — this seeds *trades*, not a positions dashboard.
- Changing the FIFO aggregator or the CLI (`schwab-positions-cli-import`).
- Seeding non-equity/non-option asset types (`MUTUAL_FUND`, `FIXED_INCOME`, `CASH_EQUIVALENT`, `CURRENCY`, futures) — skipped with a warning; add later if needed.
- Fixing the pre-existing `multiplier = 1` hardcode on the Schwab *transaction* path (`schwab_json.py:133`); only the new position-snapshot legs get the correct option multiplier.

## Decisions

### D1: Deterministic composite id (no natural id)

Schwab `positions[]` entries have no id. Use `id = "schwab:openpos:{accountNumber}:{symbol}:{longQuantity}"` (or `shortQuantity` for shorts). This is:
- **Deterministic** → re-importing the same file is a no-op (contract idempotency).
- **Position-scoped** → one snapshot lot per symbol/side/quantity per account.

Trade-off: if the same symbol is held in two separate lots of the same quantity, they collapse into one snapshot leg. Acceptable — a snapshot already represents a netted/averaged position, not discrete fills (contract D4 risk note).

For options, `{symbol}` is the full OCC-style option symbol Schwab provides — longer, but unique per contract, which is exactly what we want (two different strikes/expiries yield different ids). The raw id field accommodates it.

### D2: `executed_at = dateRange.start` (approximate open time, ordering-safe)

No open date exists on `positions[]`. Use the file's top-level `dateRange.start` (tz-aware UTC) as the snapshot opening instant — **not** `fetchedAt`.

Rationale — this is chosen for correctness under later reconciliation, not intuition:
- The trade projection computes `opened_at = min(entry executed_at)` and `closed_at = max(exit executed_at)`, and the FIFO aggregator orders legs by `executed_at`. A snapshot opening leg MUST sort *before* any closing leg that arrives in the same or a later import, or it will not be matched as the opening leg.
- `fetchedAt` is "now" (when the snapshot was pulled). If the user pulls a snapshot today but later imports history where the position was **already closed** last week, `fetchedAt` (today) would be *after* the close → `opened_at > closed_at` and the FIFO match fails. This is a real ordering bug.
- `dateRange.start` means "this position existed at least since the window start". It is guaranteed to precede every transaction in that window (including the close), so the snapshot opening leg always sorts first. Holding-period is then conservatively *over*-estimated rather than producing an invalid ordering.

Consequence: `opened_at` remains approximate (window start, not true fill), so holding-period stats are skewed early; round-trip P&L stays correct (price-based). This is the contract's approximate path (D4/path 2). When the real opening execution later arrives it supersedes the snapshot (D3), correcting `opened_at` exactly.

### D3: Reconciliation relies on the contract's snapshot-replace rule

Because Schwab has no shared id, a later real opening execution cannot collapse via `bulk_upsert`. Instead the contract's snapshot-replace rule applies: position snapshots are the source of truth for the account's open lots. On each import, existing `open_position` legs for the account's `(symbol, conid, asset_class)` instruments that are absent from (or quantity-changed in) the new snapshot set are removed before seeding; and where a real `imported` opening execution exists for the instrument, it supersedes the `open_position` leg. The aggregator's instrument key is `(symbol, conid, asset_class)` with `conid = None` for Schwab. This adapter adds **no** reconciliation code — it only produces records the contract rule understands (correct symbol / asset_class / direction / quantity).

### D4: Price, direction, and asset-type mapping (EQUITY + OPTION)

Direction / quantity / price:
- `longQuantity > 0` → direction LONG, quantity `longQuantity`, price `averageLongPrice` (fallback `averagePrice`).
- `shortQuantity > 0` → direction SHORT, quantity `shortQuantity`, price `averagePrice` (short avg).

Asset type (reuse the existing `_map_asset_class`, which already knows `EQUITY` and `OPTION`):
- `assetType = "EQUITY"` → `AssetClass.EQUITY`, `multiplier = 1`, symbol = `instrument.symbol` as-is.
- `assetType = "OPTION"` → `AssetClass.OPTION`, `multiplier = 100`, symbol = `instrument.symbol` as-is (Schwab already provides the OCC-style option symbol; no re-encoding here). The multiplier is required so the contract's price/P&L math (`(exit_price − entry_price) × qty × multiplier`) is correct; a `multiplier = 1` option lot would understate P&L by ~100×.
- Any other `assetType` (`MUTUAL_FUND`, `FIXED_INCOME`, `CASH_EQUIVALENT`, `CURRENCY`, futures, …) → skip with a warning. Seeding those correctly needs asset-specific handling that is out of scope for this change.

Note (pre-existing, not fixed here): the Schwab *transaction* path hardcodes `multiplier = 1` even for options (`schwab_json.py:133`). This change sets the correct option multiplier only on the **position-snapshot** legs it emits; it deliberately does not touch the transaction path (surgical-changes rule). Flagged as an existing inconsistency.

## Risks / Trade-offs

- **[Risk] Approximate `opened_at`** → holding-period metrics skewed. Mitigation: `open_position` origin flags these; contract documents the caveat. Accepted.
- **[Risk] Quantity-change between snapshots yields a new id** → a partially-closed position re-imported later has a different `longQuantity`, so a new snapshot leg id. Mitigation: the supersede guard + FIFO closing legs from `transactions` keep the trade projection correct; stale snapshot legs for a since-closed quantity are superseded by real executions. Covered by an integration test.
- **[Risk] Contract guard incorrect** → phantom double-open. Mitigation: the guard and its test live in `open-position-seeding`; this change adds a Schwab-flavoured integration test (snapshot open + later real open of same position → one lot).
- **[Risk] Contract not landed** → no `is_open_position` field. Mitigation: sequence after `open-position-seeding`.

## Migration Plan

1. Land `open-position-seeding` (contract) and ideally `schwab-positions-cli-import` (wrapped format).
2. Land this adapter (parser `positions[]` handling + tests).
3. Existing Schwab imports begin seeding open lots from `positions[]` automatically.

Rollback: revert the parser change; `positions[]` returns to being written-but-ignored. Contract untouched.

## Open Questions

- Resolved: **`executed_at` = `dateRange.start`** (ordering-safe under later reconciliation — see D2).
- Resolved: **asset types = EQUITY + OPTION** (option `multiplier = 100`, OCC symbol as-is — see D4); other types skipped with a warning.
- Remaining: if Schwab ever exposes a per-lot open date on `positions[]`, prefer it over `dateRange.start`. None observed today.
