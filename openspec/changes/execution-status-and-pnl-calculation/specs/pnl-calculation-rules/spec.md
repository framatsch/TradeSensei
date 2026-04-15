## ADDED Requirements

### Requirement: Execution P&L is broker truth only

The system SHALL only display execution-level P&L when the execution has status IMPORTED and contains broker-reported P&L. For all other cases, execution P&L SHALL display "—" to indicate calculation happens at trade level.

#### Scenario: Imported execution with broker P&L
- **WHEN** execution status is IMPORTED
- **AND** execution.pnl field is not null
- **THEN** UI displays the broker-reported P&L value
- **AND** value is formatted to 2 decimal places

#### Scenario: Imported execution without broker P&L
- **WHEN** execution status is IMPORTED
- **AND** execution.pnl field is null (opening leg)
- **THEN** UI displays "—"

#### Scenario: Edited execution P&L display
- **WHEN** execution status is EDITED
- **THEN** UI displays "—" regardless of pnl field value
- **AND** tooltip explains "P&L calculated at trade level"

#### Scenario: Manual execution P&L display
- **WHEN** execution status is MANUAL
- **THEN** UI displays "—"
- **AND** tooltip explains "P&L calculated at trade level"

### Requirement: Trade P&L is source of truth

The system SHALL calculate trade P&L using broker-reported execution P&L only when ALL executions have status IMPORTED. Otherwise, trade P&L SHALL be calculated from VWAP entry/exit prices.

#### Scenario: All executions imported with broker P&L
- **WHEN** all trade executions have status IMPORTED
- **AND** all closing executions have non-null pnl field
- **THEN** trade.pnl = sum of execution.pnl values
- **AND** trade P&L is displayed in trade details

#### Scenario: At least one execution is edited
- **WHEN** trade has at least one execution with status EDITED
- **THEN** trade.pnl is calculated from prices: (exit_price - entry_price) * quantity * multiplier
- **AND** broker-reported execution P&L is ignored

#### Scenario: Manual execution in trade
- **WHEN** trade contains at least one MANUAL execution
- **THEN** trade.pnl is calculated from prices
- **AND** broker-reported execution P&L is ignored

#### Scenario: Trade P&L updates after execution edit
- **WHEN** user edits execution price/quantity/commission
- **THEN** trade P&L is immediately recalculated
- **AND** frontend refetches updated trade data
- **AND** new P&L is displayed within 2 seconds

### Requirement: P&L calculation uses FIFO aggregation

The system SHALL maintain FIFO (First-In-First-Out) aggregation logic in _re_aggregate_trade when calculating trade P&L from prices.

#### Scenario: LONG trade P&L calculation
- **WHEN** trade direction is LONG
- **THEN** raw_pnl = (exit_price - entry_price) * exit_quantity * multiplier
- **AND** trade.pnl = raw_pnl rounded to 10 decimal places
- **AND** trade.net_pnl = trade.pnl - total_commission

#### Scenario: SHORT trade P&L calculation
- **WHEN** trade direction is SHORT
- **THEN** raw_pnl = (entry_price - exit_price) * exit_quantity * multiplier
- **AND** trade.pnl = raw_pnl rounded to 10 decimal places
- **AND** trade.net_pnl = trade.pnl - total_commission

#### Scenario: Partial exit P&L
- **WHEN** trade has partial exit (exit_qty < entry_qty)
- **THEN** P&L is calculated only for exited quantity
- **AND** trade.closed_at remains null until fully exited

#### Scenario: Trade without exit executions
- **WHEN** trade has only entry executions (exit_qty = 0)
- **THEN** trade.pnl = null
- **AND** trade.net_pnl = null
- **AND** UI displays "—" for P&L

### Requirement: P&L precision is consistent

The system SHALL display all P&L values (execution and trade level) with exactly 2 decimal places in the UI.

#### Scenario: Positive P&L formatting
- **WHEN** P&L value is positive (e.g., 237.4567)
- **THEN** UI displays "+$237.46" in green color
- **AND** value is rounded to 2 decimals

#### Scenario: Negative P&L formatting
- **WHEN** P&L value is negative (e.g., -123.4567)
- **THEN** UI displays "-$123.46" in red color

#### Scenario: Zero P&L formatting
- **WHEN** P&L value is exactly 0.00
- **THEN** UI displays "$0.00" in neutral color

#### Scenario: Null P&L display
- **WHEN** P&L is null (not yet calculated)
- **THEN** UI displays "—" in muted color

## Definition of Done

### Unit Tests (Backend)

**File:** `backend/tests/unit/test_trade_pnl_calculation.py`

- Test: `test_trade_pnl_uses_broker_when_all_imported()`
  - Verify sum of execution P&L when all IMPORTED
- Test: `test_trade_pnl_calculates_from_prices_when_edited()`
  - Verify price-based calculation when EDITED execution exists
- Test: `test_trade_pnl_long_calculation()`
  - Verify (exit - entry) * qty * multiplier for LONG
- Test: `test_trade_pnl_short_calculation()`
  - Verify (entry - exit) * qty * multiplier for SHORT
- Test: `test_trade_pnl_partial_exit()`
  - Verify P&L calculated only for exited quantity
- Test: `test_trade_pnl_no_exit_returns_null()`
  - Verify null when no exit executions

**File:** `backend/tests/unit/test_execution_pnl_display.py`

- Test: `test_execution_pnl_null_for_edited()`
  - Verify execution.pnl handling when status=EDITED

### Integration Tests (Backend)

**File:** `backend/tests/integration/test_trade_aggregation.py`

- Test: `test_re_aggregate_updates_pnl_after_execution_edit()`
  - Edit execution price
  - Verify trade P&L recalculated
  - Verify new P&L different from broker sum

### E2E Tests (Playwright)

**File:** `frontend/tests/e2e/trade-pnl-calculation.spec.ts`

- Test: `should display trade P&L in details panel`
  - Navigate to closed trade
  - Verify P&L displayed with 2 decimals
  - Verify color coding (green=profit, red=loss)
- Test: `should update trade P&L after execution edit`
  - Edit execution price
  - Wait for refetch (max 2s)
  - Verify trade P&L updated
  - Verify execution P&L shows "—"
- Test: `should show tooltip on execution P&L dash`
  - Hover over "—" in execution P&L column
  - Verify tooltip: "P&L calculated at trade level"

**File:** `frontend/tests/e2e/pnl-display-formatting.spec.ts`

- Test: `should format positive P&L with plus sign and green`
  - Verify profit trades show "+$XXX.XX" in green
- Test: `should format negative P&L with minus sign and red`
  - Verify loss trades show "-$XXX.XX" in red
- Test: `should show dash for open positions`
  - Open trade (no exit) shows "—" for P&L

### Regression Tests

**File:** `backend/tests/integration/test_pnl_regression.py`

- Existing test: `test_pnl_regression_cross_year_trades()`
  - Must continue to pass (verify FIFO logic unchanged)
- Existing test: `test_pnl_regression_options_multiplier()`
  - Must continue to pass (verify multiplier handling)

### Coverage Requirements

- Unit tests: ≥80% coverage for _re_aggregate_trade function
- E2E tests: All P&L display scenarios covered
- Regression tests: All existing P&L tests must pass
