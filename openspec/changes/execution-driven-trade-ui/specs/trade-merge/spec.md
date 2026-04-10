## ADDED Requirements

### Requirement: Merge Trades Backend Endpoint
The system SHALL provide a `POST /api/v1/trades/merge` endpoint that combines 2 or more trades into a single trade by reassigning their `LogicalExecution` records.

#### Scenario: Successful merge of two trades
- **WHEN** a user submits `{"trade_ids": ["uuid1", "uuid2"]}` to `POST /api/v1/trades/merge`
- **THEN** the system MUST reassign all `LogicalExecution` records from both trades to a single surviving trade
- **AND** the system MUST re-aggregate the surviving trade
- **AND** the system MUST delete the now-empty source trades (except the survivor)
- **AND** the system MUST preserve metadata (notes, tags, playbook) from the oldest trade
- **AND** notes from non-surviving trades MUST be appended to the survivor's notes
- **AND** the response MUST return the merged `TradeRead`

#### Scenario: Merge validation — same symbol required
- **WHEN** a user tries to merge trades with different symbols
- **THEN** the system MUST return HTTP 422 with error "Can only merge trades with the same symbol"

#### Scenario: Merge validation — same account required
- **WHEN** a user tries to merge trades with different account IDs
- **THEN** the system MUST return HTTP 422 with error "Can only merge trades in the same account"

#### Scenario: Merge validation — minimum trades
- **WHEN** a user submits fewer than 2 trade IDs
- **THEN** the system MUST return HTTP 422 with error "At least 2 trades are required for merge"

#### Scenario: Merge validation — maximum trades
- **WHEN** a user submits more than 10 trade IDs
- **THEN** the system MUST return HTTP 422 with error "Cannot merge more than 10 trades at once"

#### Scenario: Authorization check
- **WHEN** a user tries to merge trades they do not own
- **THEN** the system MUST return HTTP 404

### Requirement: Merge from Trade List (Bulk Select)
The `BulkActionToolbar` SHALL display a "Merge" button when 2 or more trades with the same symbol are selected.

#### Scenario: Merge button visibility
- **WHEN** the user selects 2+ trades in the trade list with the same symbol
- **THEN** a "Merge" button MUST appear in the `BulkActionToolbar`

#### Scenario: Merge button disabled state
- **WHEN** the user selects 2+ trades with different symbols
- **THEN** the "Merge" button MUST either not appear or be disabled with a tooltip: "Can only merge trades with the same symbol"

#### Scenario: Clicking Merge from toolbar
- **WHEN** the user clicks "Merge" in the toolbar
- **THEN** the `MergePreviewModal` MUST open showing the selected trades and the merged result

### Requirement: Merge from Trade Detail Page
The Trade Detail page SHALL provide a "Merge with..." option in an overflow menu.

#### Scenario: Overflow menu on detail page
- **WHEN** a user views a trade's detail page
- **THEN** a "⋮" overflow menu MUST be available in the header area
- **AND** the menu MUST include: "Edit Trade", "Merge with...", "Delete Trade"

#### Scenario: Trade picker for merge
- **WHEN** the user clicks "Merge with..." from the overflow menu
- **THEN** a `TradePickerModal` MUST open showing trades filtered to the same symbol and account
- **AND** the user MUST be able to select one or more trades to merge with

#### Scenario: Proceeding to merge preview
- **WHEN** the user selects trades in the picker and clicks "Continue"
- **THEN** the `MergePreviewModal` MUST open with the current trade + selected trades

### Requirement: Merge Preview Modal
The system SHALL display a `MergePreviewModal` showing the source trades and a preview of the merged result before confirming.

#### Scenario: Preview content
- **WHEN** the merge preview modal opens
- **THEN** it MUST display: source trade cards (symbol, quantity, execution count, PnL for each), an arrow pointing to the merged result card (combined executions count, total quantity, combined PnL), a warning message about the operation being irreversible, Cancel and "Merge Trades" buttons

#### Scenario: Confirming merge
- **WHEN** the user clicks "Merge Trades" in the preview modal
- **THEN** the system MUST call `POST /api/v1/trades/merge` with the selected trade IDs
- **AND** on success, the modal MUST close
- **AND** the trade list MUST refresh (invalidate cache)
- **AND** if on the detail page, the user MUST be redirected to the merged trade's detail page

#### Scenario: Merge failure
- **WHEN** the merge API returns an error
- **THEN** the modal MUST display the error message and remain open

### Requirement: MergeTradesRequest Schema
The backend SHALL provide a `MergeTradesRequest` Pydantic schema in the trade schemas module.

#### Scenario: Schema validation
- **WHEN** a `MergeTradesRequest` is submitted
- **THEN** `trade_ids` MUST be a list of UUIDs with `min_length=2` and `max_length=10`

### Requirement: Reassign Execution to Another Trade
The system SHALL allow a user to move a single `LogicalExecution` from its current trade to a different existing trade via `POST /api/v1/executions/{execution_id}/reassign`.

#### Scenario: Successful reassign
- **WHEN** a user submits `{"target_trade_id": "uuid"}` to `POST /api/v1/executions/{execution_id}/reassign`
- **THEN** the system MUST update the execution's `trade_id` to the target trade
- **AND** the system MUST re-aggregate both the source trade (fewer executions) and the target trade (more executions)
- **AND** if the source trade has zero remaining executions, it MUST be deleted
- **AND** the response MUST return the updated `LogicalExecutionRead` and both affected `TradeRead` objects (source and target, or only target if source was deleted)

#### Scenario: Reassign validation — same symbol required
- **WHEN** a user tries to reassign an execution to a trade with a different symbol
- **THEN** the system MUST return HTTP 422 with error "Execution symbol must match target trade symbol"

#### Scenario: Reassign validation — same account required
- **WHEN** a user tries to reassign an execution to a trade in a different account
- **THEN** the system MUST return HTTP 422 with error "Execution and target trade must belong to the same account"

#### Scenario: Authorization check
- **WHEN** a user tries to reassign an execution they do not own, or to a trade they do not own
- **THEN** the system MUST return HTTP 404

### Requirement: Detach Execution as New Trade
The system SHALL allow a user to detach a single `LogicalExecution` from its current trade and create a new trade containing only that execution via `POST /api/v1/executions/{execution_id}/detach`.

#### Scenario: Successful detach
- **WHEN** a user submits `POST /api/v1/executions/{execution_id}/detach`
- **THEN** the system MUST create a new `Trade` record
- **AND** the system MUST reassign the execution's `trade_id` to the new trade
- **AND** the system MUST re-aggregate the source trade (fewer executions) and the new trade
- **AND** if the source trade has zero remaining executions, it MUST be deleted
- **AND** the response MUST return the new `TradeRead` and optionally the updated source `TradeRead`

#### Scenario: Detach from a single-execution trade
- **WHEN** a user tries to detach the only execution from a trade
- **THEN** the system MUST return HTTP 422 with error "Cannot detach the only execution from a trade — use delete instead"

### Requirement: Execution Row Context Menu — Routing Actions
The execution row context menu (⋮) SHALL include "Move to..." and "Detach as new Trade" options in addition to "Edit" and "Delete".

#### Scenario: Context menu options
- **WHEN** a user clicks the overflow menu (⋮) on an execution row
- **THEN** the menu MUST show: "Edit", "Move to...", "Detach as new Trade", "Delete"

#### Scenario: "Move to..." opens trade picker
- **WHEN** a user clicks "Move to..." in the context menu
- **THEN** a `TradePickerModal` MUST open filtered to the same symbol and account
- **AND** the user MUST select a target trade
- **AND** on selection, the system MUST call `POST /api/v1/executions/{id}/reassign` with the target trade ID
- **AND** both the current trade detail and the execution legs table MUST refresh

#### Scenario: "Detach as new Trade" confirmation
- **WHEN** a user clicks "Detach as new Trade" in the context menu
- **THEN** a confirmation dialog MUST appear: "This will remove this execution from the current trade and create a new trade. Continue?"
- **AND** on confirmation, the system MUST call `POST /api/v1/executions/{id}/detach`
- **AND** the execution legs table MUST refresh (execution disappears from current trade)
- **AND** a success toast MUST show with a link to the newly created trade
