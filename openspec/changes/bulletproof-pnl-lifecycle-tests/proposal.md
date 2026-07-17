## Why

Four recently archived changes plus the active `combo-import-leg-model` change
made **fundamental modifications to import behaviour, P&L calculation, and the
trade open/close lifecycle**:

- `2026-07-13-schwab-positions-cli-import` — wrapped Schwab schema; unmatched
  opening trades become open lots.
- `2026-07-13-split-adjusted-execution-markers` — on-the-fly split-adjusted vs.
  raw price/quantity in the executions view.
- `2026-07-15-schwab-real-transactions-import` — direction derived from
  `amount` sign + `positionEffect`; short-trade handling through the shared
  FIFO pipeline.
- `trade-bulk-endpoints` — bulk delete / tag / playbook (P&L-neutral, but part
  of the trade lifecycle surface).
- `combo-import-leg-model` — leg-native COMBO import, exact-set open↔close
  matching, cross-import combo close, combo P&L-preservation invariant.

An audit of the existing test suite found that the **happy paths are well
covered**, but several P&L- and lifecycle-critical paths are **not** exercised,
and one regression guard is silently dead. These gaps mean a future refactor
could break realized P&L or the open/close lifecycle without any test failing.

Confirmed gaps:

1. **Cross-import seed lots are effectively untested.** `aggregate_executions_fifo`'s
   `seed_open_lots` / `seed_orphaned_lots` parameters — the mechanism that lets a
   position opened in one import file be closed by a later file — are **never**
   passed in any unit test. The only coverage is
   `backend/tests/integration/test_pnl_regression.py`, which:
   - **is dead code**: it unpacks `_parse_raw_files(paths)` as a 3-tuple
     (`raw_records, cash_transactions, corporate_actions`) but the helper returns
     a **2-tuple** (`raw_records, corporate_actions`) → `ValueError` on unpack;
   - **always skips** in CI because it depends on real `TraderJournal_20xx.xml`
     files that are absent, so the broken unpack never surfaces.
   The single-instrument cross-year seed-lot + split P&L path is therefore
   **unverified**.

2. **The `seed_orphaned_lots` matching path** (aggregator "orphaned lot" fill,
   which reconstructs P&L when a close arrives before its open across imports)
   has no dedicated unit test.

3. **No Schwab SHORT round-trip lifecycle test.** Direction derivation is tested
   at the parser level, but no test drives a Schwab `SELL_TO_OPEN → BUY_TO_CLOSE`
   short position through FIFO and asserts the resulting P&L and open/close
   lifecycle.

4. **Combo anomaly P&L isolation is asserted only indirectly.** No test proves
   that an unmatched combo close (Decision 6) contributes exactly **zero** closed
   P&L and that the surrounding single-instrument totals are neither lost nor
   double-counted.

5. **The two multi-leg VWAP aggregator tests are `@skip`-ped**
   ("FIFO aggregator behavior pending verification") and, on inspection, encode a
   **wrong** expectation (they assert a single VWAP-collapsed trade and contain
   arithmetic errors — e.g. `56862/150 = 378.41` while `(100·373.62 + 50·375)/150
   = 373.08`). FIFO does not collapse lots into one VWAP trade; it produces one
   closed trade per matched lot. Multi-leg entry/exit P&L precision is thus
   unverified.

## What Changes

This change is **test- and correctness-focused**. It adds the missing edge-case
tests, fixes the two defects that block real coverage, and corrects the
misspecified VWAP tests — making the import P&L and open/close lifecycle
bulletproof against future refactors.

- **Fix the dead cross-import regression test.** Correct the tuple unpack in
  `test_pnl_regression.py` to match the 2-tuple `_parse_raw_files` contract so
  the test actually runs when data is present.
- **Add committed synthetic cross-import fixtures** (a two-file open→close set,
  including a cross-file split on a seed lot) so the single-instrument
  cross-import seed-lot + split P&L path is verified in CI **without** the real
  `TraderJournal_20xx.xml` files.
- **Add direct aggregator unit tests** for `seed_open_lots` and
  `seed_orphaned_lots`, covering: seed lot closed by a later execution (carries
  `db_trade_id` for UPDATE), split applied to a seed lot before its close,
  orphaned-lot fill P&L reconstruction, and direction-mismatch non-matching.
- **Add a Schwab SHORT round-trip lifecycle test** (`SELL_TO_OPEN → BUY_TO_CLOSE`)
  through the shared FIFO pipeline asserting direction, open/close lifecycle, and
  P&L sign.
- **Add a combo anomaly P&L-isolation test** proving an unmatched combo close
  contributes zero closed P&L and does not corrupt neighbouring totals.
- **Rewrite the two skipped VWAP tests to match FIFO semantics** (per-lot closed
  trades with correct per-lot P&L, multiplier applied) and remove `@skip`.
- **Add a combo cross-import + split interaction guard** ensuring combo grouping
  and single-instrument split adjustment coexist without altering total P&L.

## Non-goals

- No production code behaviour change to the aggregator, parsers, import
  service, or execution service (only test code + one broken test-helper unpack
  fix + new fixtures).
- No new broker features, no Schwab combo grouping, no live-broker sync.
- No frontend changes.

## Impact

- Affected specs: `aggregation-integration-testing` (extended with explicit
  cross-import, short-lifecycle, combo-anomaly, and multi-leg-VWAP P&L
  requirements).
- Affected code (tests + fixtures only, plus one test-helper fix):
  - `backend/tests/integration/test_pnl_regression.py` — fix 2-tuple unpack.
  - `backend/tests/test_aggregator.py` — rewrite the two VWAP tests to FIFO
    semantics; add `seed_open_lots` / `seed_orphaned_lots` unit tests.
  - `backend/tests/test_aggregator_seed_lots.py` (new) — dedicated seed-lot unit
    coverage (or add to `test_aggregator.py`).
  - `backend/tests/test_schwab_json_import.py` — add SHORT round-trip lifecycle
    test.
  - `backend/tests/test_combo_invariants.py` — add anomaly P&L-isolation +
    combo/split interaction tests.
  - `backend/tests/integration/test_cross_import_seed_regression.py` (new) —
    synthetic two-file cross-import seed-lot + split regression.
  - New fixtures under `backend/tests/fixtures/ibkr/` (committed, CI-safe):
    `seed_open_year1.xml`, `seed_close_year2.xml` (open→close across files with a
    cross-file split).
- No production runtime code, no DB migration, no API contract change.
