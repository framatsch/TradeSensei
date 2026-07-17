# aggregation-integration-testing Specification

## Purpose
TBD - created by archiving change isolated-raw-layer-architecture. Update Purpose after archive.
## Requirements
### Requirement: Integration Testing & Verification
The system MUST prove the mathematical correctness of the new architecture via integration tests.

#### Scenario: PnL Baseline Validation
- **WHEN** the automated integration test is executed with historical XML files
- **THEN** the aggregated PnL in the database (filtered by imported executions and `closed_at` on a yearly basis) MUST exactly match the output of the `flex_query_aggregation.py` script.

### Requirement: Ground-Truth Generator Script
The system SHALL provide a `flex_query_aggregation.py` script to parse IBKR XML flex queries and generate the ground-truth database PnL, factoring in commissions, `TransactionTax`, and `CashTransaction` items (FEE category).

#### Scenario: Running the ground-truth generator
- **WHEN** the script is executed against historical XML files
- **THEN** it SHALL calculate commissions using `max(abs(ibCommission), abs(commission))` and subtract taxes and fees from the net performance.

### Requirement: Cross-import seed-lot P&L is verified in CI with committed fixtures
The system SHALL prove, using committed synthetic fixtures that do NOT require
proprietary broker data, that a single-instrument position opened in one import
file and closed in a later import file produces the correct realized P&L and is
UPDATEd (not duplicated). The verification SHALL include a corporate-action split
dated between the two files so that the persisted seed lot is split-adjusted
before the closing execution matches.

#### Scenario: Position opened in file A is closed by file B without duplication
- **WHEN** import file A opens a single-instrument LONG position that remains open, and a later import file B contains the matching closing execution
- **THEN** exactly one closed trade results for that position (the seed lot is updated, not re-created)
- **THEN** no duplicate open trade remains for that position after file B

#### Scenario: Seed lot is split-adjusted before its cross-file close
- **WHEN** a corporate-action split is dated between file A (open) and file B (close)
- **THEN** the closed trade's quantity equals the pre-split quantity × ratio and its entry price equals the pre-split entry price ÷ ratio
- **THEN** the realized P&L is computed against the split-adjusted entry price

#### Scenario: Cross-import DB P&L equals in-memory ground truth
- **WHEN** files A and B are imported sequentially into the database
- **THEN** the sum of DB realized P&L per year equals the in-memory ground-truth aggregation over both files (tolerance < 0.01)

---

### Requirement: The seed-lot aggregator parameters are covered by direct unit tests
The system SHALL provide unit tests that call the FIFO aggregator directly with
`seed_open_lots` and `seed_orphaned_lots` (using lightweight stubs, no database),
proving the seed mechanism independently of the import service and DB.

#### Scenario: A closed seed lot carries its db_trade_id for UPDATE
- **WHEN** a seed open lot is closed by an incoming opposite-direction execution
- **THEN** the resulting closed trade carries `db_trade_id` equal to the seed lot's id (so the caller issues an UPDATE, not an INSERT)

#### Scenario: An orphaned seed lot is filled and its P&L reconstructed
- **WHEN** a `seed_orphaned_lots` entry (a persisted closing leg awaiting its open) is matched by a later opening execution
- **THEN** the filled trade's `pnl`/`net_pnl` are reconstructed from the true entry price
- **THEN** no `0.001` sentinel entry price remains on the filled trade

#### Scenario: Same-direction seed lot does not match
- **WHEN** a seed open lot and an incoming execution share the same direction
- **THEN** the seed lot is not closed and the position increases (the seed lot remains open)

---

### Requirement: Multi-leg FIFO partial-close P&L precision is verified (not skipped)
The system SHALL verify multi-leg / partial-close FIFO P&L with executed
(non-skipped) tests that assert the aggregator's true per-lot FIFO behaviour:
each opening lot closed by a counter-execution yields its own closed trade with
per-lot gross P&L `(exit − lot_entry) × matched_qty × multiplier`, correct
commission proration, and correct per-lot timestamps. Tests SHALL NOT assert a
single VWAP-collapsed trade, because the production aggregator does not collapse
lots.

#### Scenario: Two opening lots closed by one execution yield two closed trades
- **WHEN** BUY 100 @ P1, then BUY 50 @ P2, then SELL 150 @ Pexit are aggregated
- **THEN** two closed trades result: one for the 100-share lot and one for the 50-share lot
- **THEN** each trade's gross P&L equals `(Pexit − lot_entry) × lot_qty × multiplier`

#### Scenario: Options partial closes apply the multiplier per lot
- **WHEN** BUY 10 contracts @ 5.50 (multiplier 100), then SELL 6 @ 5.75, then SELL 4 @ 5.80 are aggregated
- **THEN** two closed trades result with P&L `(5.75 − 5.50) × 6 × 100 = 150` and `(5.80 − 5.50) × 4 × 100 = 120`
- **THEN** the combined realized P&L equals 270 across the two trades

---

### Requirement: Unmatched combo close contributes zero P&L (isolation verified)
The system SHALL verify that an unmatched combo close (a combo-eligible closing
order that fails exact contract-set/quantity matching — a data anomaly) leaves
its position open and contributes exactly zero closed P&L, and that surrounding
single-instrument and matched-combo totals are neither lost nor double-counted.

#### Scenario: Anomalous combo close adds no realized P&L
- **WHEN** a combo-eligible closing order fails exact matching and its position is left open
- **THEN** that position's `closed_at` is null and its `pnl` is null
- **THEN** the total realized P&L over all trades equals the combo-agnostic ground truth for the matched portion, with the anomalous position contributing 0

#### Scenario: Combo grouping and a split coexist without changing total P&L
- **WHEN** an import contains both a combo order and a single-instrument position affected by a corporate-action split
- **THEN** the total realized P&L is identical between the combo-agnostic and combo-aware aggregation paths

---

### Requirement: Schwab short round-trip lifecycle and P&L are verified end-to-end
The system SHALL verify that a Schwab `SELL_TO_OPEN` followed by a
`BUY_TO_CLOSE` on the same symbol imports through the shared FIFO pipeline as a
single closed SHORT trade with the correct open/close lifecycle and P&L sign.

#### Scenario: Short position opened then covered yields one closed SHORT trade
- **WHEN** a Schwab file contains a `SELL_TO_OPEN` and a later `BUY_TO_CLOSE` on the same symbol
- **THEN** exactly one closed trade results with `direction = SHORT`
- **THEN** `opened_at` corresponds to the opening leg and `closed_at` to the closing leg
- **THEN** the trade shows a profit when the close price is below the open price, and the P&L equals the in-memory FIFO ground truth

