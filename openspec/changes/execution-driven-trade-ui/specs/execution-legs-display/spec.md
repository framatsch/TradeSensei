## ADDED Requirements

### Requirement: Execution Summary Card
The Trade Detail page SHALL display an `ExecutionSummaryCard` component showing computed aggregate values derived from the trade's `LogicalExecution` records.

#### Scenario: Displaying computed values for a closed trade
- **WHEN** a user views a closed trade with 2 BUY legs and 1 SELL leg
- **THEN** the system MUST display: VWAP Entry Price, VWAP Exit Price, Total Quantity, Total Commission, Stop Loss, Take Profit
- **AND** each value MUST be clearly labeled as "Computed"
- **AND** a subtitle MUST indicate the execution count (e.g., "Values are computed from 3 execution legs below")

#### Scenario: Displaying values for an open trade
- **WHEN** a user views an open trade (no closing executions)
- **THEN** Exit Price MUST display "—"
- **AND** all entry-side values (entry price, total quantity) MUST still be computed from opening executions

### Requirement: Execution Legs Table
The Trade Detail page SHALL display an `ExecutionLegsTable` component below the summary card, showing each `LogicalExecution` as a row.

#### Scenario: Table columns
- **WHEN** the execution legs table is rendered
- **THEN** it MUST show columns: row number (#), Date (`executed_at`), Side (BUY/SELL badge), Qty, Price, Commission, P&L, Status badge

#### Scenario: Chronological ordering
- **WHEN** a trade has multiple execution legs
- **THEN** the rows MUST be sorted by `executed_at` ascending (oldest first)

#### Scenario: Collapsible behavior
- **WHEN** the execution legs section is first loaded
- **THEN** it MUST be expanded by default
- **AND** it MUST provide a collapse/expand toggle

### Requirement: Execution Status Badge
Each execution row SHALL display a colored status badge indicating its lineage.

#### Scenario: Status badge rendering
- **WHEN** an execution has `status: "imported"`
- **THEN** a blue badge with text "imported" MUST be displayed
- **WHEN** an execution has `status: "manual"`
- **THEN** a purple badge with text "manual" MUST be displayed
- **WHEN** an execution has `status: "merged"`
- **THEN** an orange badge with text "merged" MUST be displayed
- **WHEN** an execution has `status: "split"`
- **THEN** a cyan badge with text "split" MUST be displayed

### Requirement: Side Badge (BUY/SELL)
Each execution row SHALL display a direction badge using the existing color conventions.

#### Scenario: BUY/SELL display
- **WHEN** an execution's direction matches the trade's opening direction
- **THEN** it MUST display "BUY" with a green badge (for LONG) or "SELL" with a red badge (for SHORT)
- **WHEN** an execution's direction opposes the trade's opening direction
- **THEN** it MUST display the opposing side with the appropriate color

### Requirement: Inline Edit on Execution Rows
Users SHALL be able to click an execution row to enter inline edit mode for price, quantity, and commission fields.

#### Scenario: Entering inline edit mode
- **WHEN** a user clicks on an execution row (desktop)
- **THEN** the price, quantity, and commission cells MUST become editable input fields
- **AND** the row MUST show Save (checkmark) and Cancel (X) action buttons

#### Scenario: Saving inline edit
- **WHEN** a user modifies the price and clicks Save
- **THEN** the system MUST call `PATCH /api/v1/executions/{id}` with the updated fields
- **AND** the execution summary card MUST refresh with recomputed values

#### Scenario: Canceling inline edit
- **WHEN** a user presses Escape or clicks Cancel
- **THEN** the row MUST revert to display mode with original values

### Requirement: Execution Row Context Menu
Each execution row SHALL provide a context menu with additional actions.

#### Scenario: Context menu options
- **WHEN** a user clicks the overflow menu (⋮) on an execution row
- **THEN** the menu MUST show: "Edit", "Delete"
- **AND** "Delete" MUST show a confirmation prompt before executing

#### Scenario: Deleting an execution via context menu
- **WHEN** a user confirms deletion of an execution
- **THEN** the system MUST call `DELETE /api/v1/executions/{id}`
- **AND** the execution legs table and summary card MUST refresh

### Requirement: Add Execution Button
The execution legs section SHALL display an "Add Execution" button that opens the `AddExecutionModal`.

#### Scenario: Button placement and visibility
- **WHEN** the execution legs section is rendered
- **THEN** an "+ Add Execution" button MUST be visible in the section header (top-right)
- **AND** the button MUST use the primary accent style (`bg-[#6063dd] text-white`)

### Requirement: Replace Flat Execution Details Grid
The current flat "Execution Details" grid in `TradeDetailPage` SHALL be replaced by the new `ExecutionSummaryCard` + `ExecutionLegsTable` combination.

#### Scenario: Layout change
- **WHEN** the Trade Detail page is rendered
- **THEN** the old 6-field grid (Entry Price, Exit Price, Quantity, Commission, Stop Loss, Take Profit) MUST be replaced
- **AND** the `ExecutionSummaryCard` MUST appear in its place
- **AND** the `ExecutionLegsTable` MUST appear directly below the summary card

### Requirement: Chart Execution Markers
The `TradeChart` component SHALL render individual execution markers for each `LogicalExecution` instead of the current single ENTRY/EXIT pair. When multiple executions fall on the same candle, they SHALL be aggregated into a single marker with a combined label.

#### Scenario: Single execution per candle
- **WHEN** a trade has one BUY execution on Jan 15 and one SELL execution on Jan 20 (daily chart)
- **THEN** the chart MUST render an `arrowUp` marker on the Jan 15 candle with label `"+25 @ $373.62"`
- **AND** an `arrowDown` marker on the Jan 20 candle with label `"-25 @ $377.96"`
- **AND** entry markers MUST use color `#00d2ff` (Electric Cyan) with `position: "belowBar"`
- **AND** exit markers MUST use color `#f0abfc` (Bright Fuchsia) with `position: "aboveBar"`

#### Scenario: Multiple executions on the same candle
- **WHEN** two BUY executions land on the same candle (e.g., +25 @ $373.62 and +10 @ $375.00 both on Jan 15 daily)
- **THEN** the chart MUST render a single aggregated `arrowUp` marker on that candle
- **AND** the label MUST show the combined quantities and prices, e.g., `"+25+10 @ $373/$375"`
- **AND** the marker size MUST be `2` (same as current)

#### Scenario: Mixed entries and exits on the same candle
- **WHEN** both a BUY and a SELL execution land on the same candle (e.g., intraday scale-in and partial exit on the same day in daily view)
- **THEN** the chart MUST render two separate markers: one `arrowUp` (belowBar) for entries and one `arrowDown` (aboveBar) for exits
- **AND** each marker MUST aggregate its respective executions independently

#### Scenario: Snap to nearest candle
- **WHEN** an execution's `executed_at` timestamp does not exactly match a candle's open time
- **THEN** the marker MUST snap to the nearest available candle time (same logic as current implementation)

#### Scenario: Open trade (no exit markers)
- **WHEN** a trade has only entry executions and no closing executions
- **THEN** only entry `arrowUp` markers MUST be rendered
- **AND** no exit `arrowDown` markers MUST appear

#### Scenario: Chart data source
- **WHEN** the `TradeChart` receives execution data
- **THEN** it MUST source execution timestamps from the trade's `LogicalExecution` records (via props or the `useTradeExecutions` hook)
- **AND** it MUST NOT use the trade-level `opened_at`/`closed_at` for marker placement
