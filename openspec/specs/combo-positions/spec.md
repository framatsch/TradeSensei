# combo-positions Specification

## Purpose
Define expected behavior for COMBO trade creation, aggregation, API representation,
and UI rendering.
## Requirements
### Requirement: User can create a COMBO position trade
The system SHALL allow an authenticated user to create a trade with `is_combo: true`. For a COMBO trade the top-level `asset_class` SHALL be null and `entry_price`, `exit_price`, `quantity` SHALL be null. The trade's combined `pnl`, `commission`, `opened_at`, and `closed_at` SHALL be computed from its execution legs.

#### Scenario: Successful COMBO trade creation
- **WHEN** a user sends `POST /api/v1/trades` with `{"symbol": "AAPL", "is_combo": true, "direction": "LONG"}`
- **THEN** the API returns 201 with `is_combo: true`, `asset_class: null`, `entry_price: null`, `exit_price: null`, `quantity: null`

#### Scenario: Non-COMBO trade is unaffected
- **WHEN** a user sends `POST /api/v1/trades` without `is_combo` (or with `is_combo: false`)
- **THEN** `is_combo` is `false` in the response and all existing aggregation behavior applies

---

### Requirement: COMBO trade re-aggregation skips VWAP fields
The system SHALL skip computing `entry_price`, `exit_price`, and `quantity` during re-aggregation of a COMBO trade (those fields SHALL remain `null`). The system SHALL still compute `SUM(commission)`, `MIN(opened_at)`, and `MAX(closed_at)` from non-deleted legs. P&L SHALL be computed as `SUM(ex.pnl)` across legs that carry broker-reported P&L; if no leg carries broker P&L, `trade.pnl` SHALL remain `null`.

#### Scenario: Adding a leg to a COMBO trade does not set entry_price
- **WHEN** an execution leg with `price = 150.00, quantity = 100` is added to a COMBO trade
- **THEN** the trade's `entry_price` remains `null` and `quantity` remains `null`
- **THEN** the trade's `commission` reflects the leg's commission contribution

#### Scenario: COMBO pnl sums broker-reported leg P&Ls
- **WHEN** a COMBO trade has two legs with broker-reported `pnl = 200` and `pnl = -50`
- **THEN** the trade's `pnl` equals `150`

#### Scenario: COMBO pnl is null when no broker P&L on any leg
- **WHEN** a COMBO trade has legs with no broker-reported P&L (all `pnl = null`)
- **THEN** the trade's `pnl` is `null`

#### Scenario: COMBO net_pnl is pnl minus total commission
- **WHEN** a COMBO trade has `pnl = 150` and `commission = 10`
- **THEN** `net_pnl` equals `140`

---

### Requirement: COMBO execution legs carry per-leg asset_class and multiplier
The system SHALL allow specifying `asset_class` and `multiplier` per execution leg when creating a manual leg on a COMBO trade. When provided, these values override the parent trade's values for that leg. This enables an equity leg to carry `multiplier=1` and an option leg to carry `multiplier=100` within the same COMBO trade.

#### Scenario: Option leg created with multiplier 100
- **WHEN** a user adds an execution leg to a COMBO trade with `{"asset_class": "OPTION", "multiplier": 100, "price": 5.00, "quantity": 1}`
- **THEN** the leg is stored with `asset_class = "OPTION"` and `multiplier = 100`
- **THEN** the parent COMBO trade's `entry_price`, `exit_price`, `quantity` remain `null`

#### Scenario: Equity leg uses multiplier 1
- **WHEN** a user adds an execution leg to a COMBO trade with `{"asset_class": "EQUITY", "multiplier": 1, "price": 150.00, "quantity": 100}`
- **THEN** the leg is stored with `multiplier = 1`

#### Scenario: Non-COMBO leg creation is unaffected
- **WHEN** a user adds an execution leg to a standard (non-COMBO) trade without specifying `asset_class` or `multiplier`
- **THEN** the leg inherits `asset_class` and `multiplier` from the parent trade (existing behaviour unchanged)

---

### Requirement: `is_combo` is immutable after trade creation
The system SHALL NOT allow changing `is_combo` via `PATCH /api/v1/trades/{id}`. The field SHALL be absent from `TradeUpdate` and ignored if sent.

#### Scenario: PATCH with is_combo field is ignored
- **WHEN** a user sends `PATCH /api/v1/trades/{id}` with `{"is_combo": false}` on a COMBO trade
- **THEN** the API returns 200 and `is_combo` remains `true`

---

### Requirement: TradeRead exposes is_combo
The system SHALL include `is_combo: bool` in every `TradeRead` response so clients can render the appropriate UI.

#### Scenario: COMBO trade read includes flag
- **WHEN** a client fetches `GET /api/v1/trades/{id}` for a COMBO trade
- **THEN** the response includes `is_combo: true`

#### Scenario: Standard trade read includes flag as false
- **WHEN** a client fetches a standard single-instrument trade
- **THEN** the response includes `is_combo: false`

---

### Requirement: Execution legs table shows Symbol and Asset Class for COMBO trades
The system SHALL display a `Symbol` column and an `Asset Class` column per execution leg row when the parent trade has `is_combo: true`. These columns SHALL be hidden for standard trades.

#### Scenario: COMBO trade shows per-leg symbol
- **WHEN** a user opens the trade detail page for a COMBO trade with one EQUITY leg (AAPL EQUITY) and one OPTION leg (AAPL OPTION)
- **THEN** the execution legs table has a Symbol column showing "AAPL" for both rows and an Asset Class column showing "EQUITY" and "OPTION" respectively

#### Scenario: Standard trade hides symbol column
- **WHEN** a user opens a non-COMBO trade detail page
- **THEN** no Symbol or Asset Class column is present in the execution legs table

---

### Requirement: ExecutionSummaryCard shows a per-instrument breakdown for COMBO trades
The system SHALL replace the standard flat grid in `ExecutionSummaryCard` with a per-instrument summary when the trade has `is_combo: true`. Legs SHALL be grouped by `(symbol, asset_class, conid)` so that distinct option contracts (different strikes/expiries) within the same underlying remain visible as separate rows. For each group the card SHALL show: direction (LONG/SHORT), quantity with unit label ("shares" when multiplier=1, "contracts" when multiplier>1), the multiplier value when greater than 1 (displayed as `×50`, `×100`, etc. — taken from `leg.multiplier`, never hardcoded), per-unit price (VWAP of entry legs in the group), and notional value (`quantity × price × multiplier`). Below the instrument rows, a totals row SHALL show combined commission and combined P&L (if available). The standard flat grid (VWAP Entry, VWAP Exit, Total Quantity) SHALL be hidden for COMBO trades.

#### Scenario: Vertical spread COMBO shows two contract rows
- **WHEN** a user opens the trade detail page for a COMBO trade containing a QQQ 712C leg and a QQQ 722C leg (different `conid`s)
- **THEN** the ExecutionSummaryCard shows one row for the 712C contract and a separate row for the 722C contract
- **THEN** a totals row shows combined commission and combined P&L (if broker P&L is available on legs)

#### Scenario: Covered call COMBO shows two instrument rows
- **WHEN** a user opens the trade detail page for a COMBO trade containing 100 AAPL EQUITY LONG legs and 2 AAPL OPTION SHORT legs (multiplier=100)
- **THEN** the ExecutionSummaryCard shows one row for `AAPL EQUITY — LONG — 100 shares — $150.00/share — Notional $15,000`
- **THEN** a second row shows `AAPL OPTION — SHORT — 2 contracts — $5.00/contract — Notional $1,000` (= 2 × $5.00 × 100)
- **THEN** a totals row shows combined commission and combined P&L (if broker P&L is available on legs)

#### Scenario: COMBO card hides VWAP fields
- **WHEN** a user views the ExecutionSummaryCard for a COMBO trade
- **THEN** no `VWAP Entry`, `VWAP Exit`, or `Total Quantity` tiles are visible

#### Scenario: Standard trade card is unchanged
- **WHEN** a user views the ExecutionSummaryCard for a non-COMBO trade
- **THEN** the card renders the existing flat grid layout (VWAP Entry, VWAP Exit, Total Quantity, Commission)

### Requirement: Trade detail page shows a COMBO badge for COMBO trades
The system SHALL display a "COMBO" badge near the trade title on the trade detail page when `is_combo: true`, replacing the LONG/SHORT directional badge.

#### Scenario: COMBO badge visible on detail page
- **WHEN** a user opens the trade detail page for a COMBO trade
- **THEN** a "COMBO" badge is displayed near the trade title

#### Scenario: Standard trade shows directional badge
- **WHEN** a user opens a non-COMBO trade detail page
- **THEN** the LONG/SHORT directional badge is shown (existing behavior, unchanged)

---

### Requirement: Trade list shows COMBO indicator
The system SHALL render "COMBO" in the asset-class / direction column of the trades list table for COMBO trades.

#### Scenario: COMBO trade shows COMBO in trades list
- **WHEN** a user views the trades list and one row is a COMBO trade
- **THEN** the asset-class column for that row shows "COMBO" instead of an asset class name

---

### Requirement: TradeForm supports creating a COMBO trade
The system SHALL provide a "COMBO" toggle in the trade creation form. When enabled, the `asset_class` field SHALL be hidden/disabled and `is_combo: true` SHALL be sent to the API.

#### Scenario: Enabling COMBO toggle hides asset class field
- **WHEN** a user enables the COMBO toggle in the trade creation form
- **THEN** the `asset_class` dropdown is hidden or disabled

#### Scenario: Submitting a COMBO trade sends is_combo true
- **WHEN** a user fills in the trade creation form with the COMBO toggle enabled and submits
- **THEN** the POST request body includes `is_combo: true` and omits `asset_class`

#### Scenario: Disabling COMBO toggle restores asset class field
- **WHEN** a user enables the COMBO toggle then disables it before submission
- **THEN** the `asset_class` field is re-shown and `is_combo` is `false` in the payload

---

### Requirement: Playwright E2E tests cover COMBO position UI flows
The system SHALL have automated end-to-end tests verifying the COMBO trade creation flow, the detail page badge, the execution legs table columns, and the trades list indicator.

#### Scenario: TC-101 — COMBO badge on trade detail
- **WHEN** a Playwright test navigates to the trade detail page of a seeded COMBO trade
- **THEN** a "COMBO" badge is visible near the trade title
- **THEN** no LONG/SHORT directional badge is present

#### Scenario: TC-102 — Symbol and Asset Class columns in legs table for COMBO trade
- **WHEN** a Playwright test opens the execution legs table of a COMBO trade that has one EQUITY leg and one OPTION leg
- **THEN** a "Symbol" column header is visible in the legs table
- **THEN** an "Asset Class" column header is visible in the legs table
- **THEN** the rows show the correct symbol and asset class for each leg

#### Scenario: TC-103 — No Symbol/Asset Class columns for standard trade
- **WHEN** a Playwright test opens the execution legs table of a standard (non-COMBO) trade
- **THEN** no "Symbol" column header is present in the legs table
- **THEN** no "Asset Class" column header is present in the legs table

#### Scenario: TC-104 — COMBO indicator in trades list
- **WHEN** a Playwright test navigates to the trades list page
- **THEN** the row for the seeded COMBO trade shows "COMBO" in the asset-class column

#### Scenario: TC-105 — Create COMBO trade via UI form
- **WHEN** a Playwright test opens the trade creation form, enables the COMBO toggle, fills in symbol and direction, and submits
- **THEN** the `asset_class` dropdown is not visible while the toggle is enabled
- **THEN** after submission the new trade appears in the trades list with a "COMBO" indicator

#### Scenario: TC-106 — COMBO trade detail shows no VWAP price fields
- **WHEN** a Playwright test opens the trade detail of the seeded COMBO trade
- **THEN** `entry_price` and `exit_price` are not shown as editable fields or are displayed as "—" / null

### Requirement: Execution legs carry an open_close attribute
The system SHALL persist a per-leg `open_close` attribute on each execution leg with one of the values `"O"` (opening), `"C"` (closing), or `null` (unknown / position flip / manual). The value SHALL be derived by the broker parser from the source data: for IBKR from the `openCloseIndicator` attribute, and for Schwab from the nested `transferItems[].positionEffect` field. The value SHALL be exposed in `LogicalExecutionRead`.

#### Scenario: IBKR opening leg is stored as "O"
- **WHEN** an IBKR `<Trade>` element with `openCloseIndicator="O"` is imported
- **THEN** the resulting execution leg has `open_close = "O"`

#### Scenario: IBKR closing leg is stored as "C"
- **WHEN** an IBKR `<Trade>` element with `openCloseIndicator="C"` is imported
- **THEN** the resulting execution leg has `open_close = "C"`

#### Scenario: IBKR mixed indicator is stored as null
- **WHEN** an IBKR `<Trade>` element with `openCloseIndicator="C;O"` (position flip) is imported
- **THEN** the resulting execution leg has `open_close = null`

#### Scenario: Schwab opening leg is stored as "O"
- **WHEN** a Schwab transaction whose primary trade leg has `positionEffect="OPENING"` is imported
- **THEN** the resulting execution leg has `open_close = "O"`

#### Scenario: Schwab closing leg is stored as "C"
- **WHEN** a Schwab transaction whose primary trade leg has `positionEffect="CLOSING"` is imported
- **THEN** the resulting execution leg has `open_close = "C"`

#### Scenario: Manual execution has null open_close
- **WHEN** a user creates a manual execution leg without specifying open/close
- **THEN** the leg is stored with `open_close = null`

---

### Requirement: IBKR combo orders are imported as a single COMBO trade
The system SHALL detect IBKR multi-leg option combo orders and import each combo position as a single trade with `is_combo = true`, binding the individual broker executions as its `LogicalExecution` legs (`trade_id` = the COMBO trade id). Combo-eligible executions SHALL NOT be routed through the single-instrument FIFO round-trip aggregator. An order group is combo-eligible when the executions sharing the same `brokerageOrderID` reference two or more distinct `conid` values.

#### Scenario: Vertical spread opening order becomes one open COMBO trade
- **WHEN** an IBKR file contains an opening order (`brokerageOrderID = X`) with a BUY leg on QQQ 712C and a SELL leg on QQQ 722C
- **THEN** exactly one trade is created with `is_combo = true`, `closed_at = null`
- **THEN** the trade has two execution legs: one `open_close = "O"` LONG leg (712C) and one `open_close = "O"` SHORT leg (722C)
- **THEN** the two legs are NOT emitted as separate single-instrument trades

#### Scenario: Fully closed vertical spread has four legs
- **WHEN** an IBKR file contains the opening order (BUY 712C, SELL 722C) and the closing order (SELL 712C, BUY 722C) for the same contract set
- **THEN** exactly one COMBO trade exists with `closed_at` set
- **THEN** the trade has four execution legs: two `open_close = "O"` and two `open_close = "C"`

#### Scenario: Single-instrument multi-fill is not a combo
- **WHEN** an IBKR order (`brokerageOrderID = Y`) contains multiple fills of the same single `conid`
- **THEN** no COMBO trade is created and the executions are aggregated by the normal single-instrument FIFO logic

---

### Requirement: COMBO trade P&L, commission, and timestamps are aggregated from legs on import
The system SHALL, when importing a COMBO trade, set `commission = SUM(leg.commission)` across all legs, `opened_at = MIN(open_leg.executed_at)`, `closed_at = MAX(close_leg.executed_at)` when the position is fully closed (else `null`), `pnl = SUM(close_leg.pnl)` when closing legs exist (else `null`), and `net_pnl = pnl − commission` when `pnl` is not null. The top-level `asset_class`, `quantity`, `entry_price`, and `exit_price` SHALL remain `null`.

#### Scenario: Closed vertical P&L sums broker leg P&Ls
- **WHEN** a closed QQQ vertical has closing legs with broker `pnl = 465.36` and `pnl = -392.93`
- **THEN** the COMBO trade `pnl` equals `465.36 + (-392.93)`
- **THEN** `entry_price`, `exit_price`, and `quantity` remain `null`

#### Scenario: Open combo has null pnl
- **WHEN** a combo position has only opening legs (no closing legs yet)
- **THEN** the COMBO trade `pnl` is `null` and `closed_at` is `null`

---

### Requirement: COMBO trade import direction reflects net cash flow
The system SHALL set the COMBO trade's top-level `direction` from the net cash flow of its opening legs: a net debit (net cash out) SHALL yield `LONG`, and a net credit (net cash in) SHALL yield `SHORT`. Per-leg `direction` (BUY/SELL) SHALL be preserved independently on each leg and SHALL NOT be overwritten by the combo-level direction.

#### Scenario: Bull call (debit) spread is LONG
- **WHEN** a combo opening order has a net debit (more cash paid than received across opening legs)
- **THEN** the COMBO trade `direction` is `LONG`

#### Scenario: Credit spread is SHORT
- **WHEN** a combo opening order has a net credit (more cash received than paid across opening legs)
- **THEN** the COMBO trade `direction` is `SHORT`

#### Scenario: Per-leg directions are preserved
- **WHEN** a COMBO LONG trade has a BUY leg and a SELL leg
- **THEN** the BUY leg's `direction` remains `LONG` and the SELL leg's `direction` remains `SHORT`

---

### Requirement: Combo open and close orders are matched by exact contract set
The system SHALL match a closing combo order to an open combo position only when the closing order's set of `conid`s equals the open position's contract set exactly and the absolute quantities per contract match. When multiple open positions qualify, the earliest-opened position SHALL be matched first (FIFO across positions).

Because a genuine IBKR combo order is always opened and closed as a single order, a combo-eligible closing order (an all-`C` order group with ≥2 distinct `conid`s) that fails to match an open combo position's contract set or quantities exactly is a **data anomaly**. In that case the system SHALL emit an import warning identifying the offending `brokerageOrderID`, the expected contract set, and the received contract set, and SHALL leave any related open COMBO position **open** (it SHALL NOT be closed by the anomalous order and its legs SHALL NOT be rerouted into single-instrument FIFO).

#### Scenario: Exact-set close matches the open combo
- **WHEN** an open combo position holds contracts {712C, 722C} at quantity 1 each and a closing order closes {712C, 722C} at quantity 1 each
- **THEN** the closing legs are attached to that combo position and it becomes closed

#### Scenario: Unmatched combo close raises a warning and keeps the combo open
- **WHEN** an open combo position holds {712C, 722C} and a combo-eligible closing order closes a mismatched set (e.g. only 712C, or {712C, 730C})
- **THEN** the import emits a warning naming the offending `brokerageOrderID`, the expected contract set, and the received contract set
- **THEN** the open COMBO position remains open (not closed) and its legs are not rerouted into single-instrument FIFO

---

### Requirement: Cross-import combos close previously opened COMBO trades
The system SHALL load open COMBO positions previously persisted in the database (their contract set derived from the distinct `conid`s of the non-deleted opening legs) as seed positions during import, so that a later import file containing only the closing combo order updates and closes the existing COMBO trade rather than creating a new disconnected trade.

#### Scenario: Combo opened in a prior import is closed by a later import
- **WHEN** import file A opens a QQQ vertical (COMBO trade persisted, `closed_at = null`) and a later import file B contains only the matching closing order
- **THEN** the existing COMBO trade is updated to closed (`closed_at` set, `pnl` computed) and no duplicate combo trade is created
- **THEN** the closing legs are bound to the existing COMBO trade id

---

### Requirement: Combo grouping preserves total P&L
The system SHALL guarantee that combo grouping is purely presentational with respect to profit and loss: the aggregated total realized P&L across all trades for an import MUST be identical whether or not combo grouping is applied. Each COMBO trade's `pnl` SHALL equal the sum of the broker-reported P&L of its bound closing legs, and its `commission` SHALL equal the sum of its bound legs' commissions, so that no P&L or commission is created, lost, or double-counted by grouping.

#### Scenario: Total P&L is identical with and without combo grouping
- **WHEN** the same import file is aggregated once with combo grouping disabled (single-instrument FIFO only) and once with combo grouping enabled
- **THEN** the sum of realized P&L across all resulting trades is identical (bit-identical at database numeric scale) between the two runs

#### Scenario: A COMBO trade's P&L equals the sum of its legs' P&L
- **WHEN** a COMBO trade is created from legs whose broker-reported P&L values sum to `S`
- **THEN** the COMBO trade's `pnl` equals `S` and its `commission` equals the sum of its legs' commissions

#### Scenario: Unmatched combo close contributes no P&L
- **WHEN** a combo-eligible closing order fails exact matching and the position is left open (data anomaly)
- **THEN** no closed P&L is attributed to that position and no P&L is double-counted or lost elsewhere

---

### Requirement: Execution legs table shows an Open/Close column for COMBO trades
The system SHALL display an `Open/Close` column per execution leg row when the parent trade has `is_combo: true`, rendering `open_close` as "Open" / "Close" / "—". This column SHALL be hidden for standard (non-COMBO) trades.

#### Scenario: Closed vertical shows open and close legs
- **WHEN** a user opens the trade detail page for a fully closed COMBO vertical with four legs
- **THEN** the execution legs table has an Open/Close column
- **THEN** two rows show "Open" and two rows show "Close"

#### Scenario: Standard trade hides the Open/Close column
- **WHEN** a user opens a non-COMBO trade detail page
- **THEN** no Open/Close column is present in the execution legs table

