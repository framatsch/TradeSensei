# Design: Bulletproof P&L + open/close lifecycle tests

## Context

The import → aggregation → P&L pipeline has five behaviour surfaces that were
reshaped by the recent changes. This design maps each surface to its current
coverage and the precise gap being closed, then specifies the fixtures and
test-helper fix needed to close them **in CI, without proprietary data**.

Surfaces and current coverage:

| Surface | Code | Covered today | Gap |
|---|---|---|---|
| FIFO single-instrument round-trips | `aggregator.py` `aggregate_executions_fifo` | S1–S7 synthetic, mixed-exec flip | multi-leg VWAP/partial precision (skipped, misspecified) |
| Cross-import seed lots | `aggregator.py` `seed_open_lots` / `seed_orphaned_lots` | only via a **dead, always-skipped** integration test | no unit tests; seed path unverified in CI |
| Combo build + P&L invariant | `aggregator.py` `build_combo_positions` | open/closed/anomaly build, invariant | anomaly **P&L isolation**, combo+split interaction |
| Schwab direction/lifecycle | `schwab_json.py` + FIFO | parser-level direction | no SHORT round-trip **lifecycle** P&L test |
| Split-adjusted markers | `execution.py` | raw vs adjusted, notional-invariant | (adequate — no new work) |

## Goals / Non-Goals

**Goals**
- Verify the cross-import seed-lot + split single-instrument P&L path in CI with
  committed synthetic fixtures.
- Add direct aggregator unit tests for `seed_open_lots` / `seed_orphaned_lots`.
- Prove combo-anomaly P&L isolation and combo/split coexistence.
- Verify a Schwab SHORT round-trip lifecycle and P&L.
- Replace the misspecified skipped VWAP tests with FIFO-correct assertions.
- Fix the broken `_parse_raw_files` unpack in `test_pnl_regression.py`.

**Non-Goals**
- No production behaviour changes. If a new test reveals a real production bug,
  that is reported separately, not "fixed" by weakening the test.

## Decisions

### Decision 1: The VWAP tests are misspecified — rewrite to FIFO semantics

`aggregate_executions_fifo` maintains **per-lot FIFO queues**; it does not
collapse multiple opening lots into one VWAP-averaged trade. For "BUY 100, BUY
50, SELL 150", the SELL fully closes lot 1 (100) then lot 2 (50), producing
**two** closed trades. The skipped tests assert `len(res) == 1` (wrong) and
carry arithmetic errors in their own comments.

**Chosen**: rewrite both tests to assert the true FIFO output:
- multi-leg equity: two closed trades; per-lot gross P&L = `(exit − lot_entry) ×
  match_qty × multiplier`; commission split per the aggregator's proration;
  `opened_at`/`closed_at` per matched lot.
- options multiplier=100: the existing single 10-contract lot with two partial
  closes (6 then 4) → two closed trades, each `pnl = (exit − 5.50) × qty × 100`.
  This matches the aggregator's `matched_pnl = (exit − entry) × qty ×
  multiplier` (line ~707).

**Rejected**: introducing a VWAP-collapse mode to satisfy the old assertions —
that would change production aggregation semantics and violate the P&L
invariants proven elsewhere.

The rewritten tests assert values **derived from the aggregator's documented
formula**, not hardcoded magic numbers, and are executed (no `@skip`).

### Decision 2: Committed synthetic cross-import fixtures (CI-safe)

The real cross-import guard depends on `TraderJournal_20xx.xml` (absent in CI).
Rather than rely on proprietary data, add two small committed IBKR XML fixtures
under `backend/tests/fixtures/ibkr/` (same location as the existing
`synthetic_year1/2.xml`, which are already committed and CI-safe):

- `seed_open_year1.xml`: opens one or more single-instrument positions (e.g. a
  100-share LONG that stays open at end of file) and one position that will be
  affected by a split.
- `seed_close_year2.xml`: contains the closing executions for those positions,
  plus a `<CorporateAction>` (e.g. reverse split) dated between the two files so
  the seed lot must be split-adjusted **before** the close matches.

The new integration test imports file 1, commits, imports file 2, and asserts:
- the position opened in file 1 is closed by file 2 (not duplicated),
- the closed COMBO/single trade carries the correct split-adjusted quantity and
  entry price,
- DB yearly realized P&L equals the in-memory ground-truth over both files.

This mirrors `test_sequential_import_matches_ground_truth_synthetic` but
specifically exercises the **seed-lot handoff across a commit boundary** with a
split — which the current synthetic test does not (it closes within the same
run's queue, not from a persisted seed lot loaded via the repository).

### Decision 3: Direct aggregator unit tests for seed lots

Independently of the DB, add pure unit tests calling
`aggregate_executions_fifo(..., seed_open_lots=[...], seed_orphaned_lots=[...])`
with lightweight `SeedLotLike` stubs (dataclasses, no DB), asserting:
- **Seed close carries `db_trade_id`**: a seed open lot closed by an incoming
  execution yields a closed `TradeCreate` with `db_trade_id == seed.id` (so the
  import service issues UPDATE, not INSERT).
- **Split on seed lot**: a corporate action applied to a seed lot before its
  close adjusts quantity (`× ratio`) and entry price (`÷ ratio`), and P&L is
  computed against the adjusted entry.
- **Orphaned-lot fill**: a `seed_orphaned_lots` entry (a persisted orphaned close
  awaiting its open) is filled by a later opening execution, reconstructing
  `pnl` / `net_pnl` from the true entry price (not the `0.001` sentinel).
- **Direction mismatch**: a seed lot and an incoming execution with the same
  direction do NOT match (position increases), and an orphaned lot with opposite
  direction to the open lot is left unmatched.

These make the seed mechanism verifiable without any XML or DB.

### Decision 4: Combo anomaly P&L isolation

Extend `test_combo_invariants.py` using the existing `combo_positions.xml`
anomaly scenario to assert:
- The anomalous (unmatched) combo close leaves its position **open**
  (`closed_at is None`, `pnl is None`).
- `SUM(pnl of all combo + single trades)` in the combo-aware path equals the
  combo-agnostic ground-truth P&L for the **matched** portion, with the
  anomalous position contributing exactly `0` closed P&L (no double-count, no
  loss).

### Decision 5: Schwab SHORT round-trip lifecycle

Add a fixture-driven test (extending `schwab_aggregation.json` or a small new
JSON) with a `SELL_TO_OPEN` followed by a `BUY_TO_CLOSE` on the same symbol.
Assert through the import pipeline:
- exactly one closed trade with `direction == SHORT`,
- `opened_at` = the open leg, `closed_at` = the close leg,
- P&L sign correct (profit when close price < open price for a short),
- P&L matches the in-memory FIFO ground truth.

### Decision 6: Fix the dead regression test, do not delete it

`test_pnl_regression.py` is a valuable guard when the real files ARE present
(local dev, nightly with data). Fix the unpack to the 2-tuple contract:

```python
raw_records, corporate_actions = _parse_raw_files(paths)
```

Remove the now-unused `cash_transactions` reference. Keep the `pytest.skip` guard
so CI without data still skips cleanly — but now the test is correct when it does
run. The new Decision-2 synthetic test provides the CI-level guarantee that this
test cannot (because it needs proprietary data).

## Risks / Trade-offs

- **A new test may fail because it reveals a real production defect** (e.g. seed
  P&L or orphaned-fill edge case). That is the intended value: such a failure is
  reported and fixed in production code in a follow-up, not masked by adjusting
  the test to pass. The tests assert values derived from documented formulas /
  ground-truth, not arbitrary expectations.
- **Fixture authoring risk**: synthetic XML must be structurally valid for the
  IBKR parser. Mitigated by copying the shape of `synthetic_year1/2.xml`.

## Migration Plan

None — no schema, no runtime code, no API change. Tests + fixtures + one
test-helper unpack fix only.

## Open Questions

- None blocking. If the seed-lot or orphaned-fill unit tests expose a genuine
  production discrepancy, capture it as a separate bugfix change.
