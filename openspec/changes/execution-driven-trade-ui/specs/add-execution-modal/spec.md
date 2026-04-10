## ADDED Requirements

### Requirement: Add Execution Modal Component
The system SHALL provide an `AddExecutionModal` component that allows users to create a new `LogicalExecution` for a trade.

#### Scenario: Modal structure
- **WHEN** the user clicks "+ Add Execution" on the Trade Detail page
- **THEN** a modal dialog MUST open with: a BUY/SELL segmented toggle, Quantity input (required), Price input (required), Executed At datetime input (required, defaults to now), Commission input (optional, defaults to 0), P&L input (optional), Cancel and "Add Execution" buttons

#### Scenario: BUY/SELL toggle
- **WHEN** the modal opens
- **THEN** the SELL side MUST be pre-selected (most common use: closing a position)
- **AND** the user MUST be able to switch to BUY for scaling in

### Requirement: Modal Validation
The modal SHALL validate all inputs before submission.

#### Scenario: Required field validation
- **WHEN** the user submits the form with quantity = 0 or empty price
- **THEN** the modal MUST display inline validation errors and prevent submission

#### Scenario: Positive quantity validation
- **WHEN** the user enters a negative or zero quantity
- **THEN** the error "Quantity must be greater than 0" MUST be displayed

#### Scenario: Timezone-aware datetime
- **WHEN** the user selects a date and time
- **THEN** the value MUST be converted to a timezone-aware UTC ISO string before submission

### Requirement: Modal Submission
On valid submission, the modal SHALL create a `LogicalExecution` via the API and refresh the parent trade.

#### Scenario: Successful execution creation
- **WHEN** the user submits valid execution data
- **THEN** the system MUST call `POST /api/v1/trades/{tradeId}/executions` with the form data
- **AND** on success, the modal MUST close
- **AND** the execution legs table MUST refresh to show the new execution
- **AND** the execution summary card MUST refresh with recomputed values

#### Scenario: API error handling
- **WHEN** the API returns an error (e.g., 422, 500)
- **THEN** the modal MUST display the error message from the API response
- **AND** the modal MUST remain open so the user can correct and retry

### Requirement: Mobile Responsiveness
The modal SHALL be fully functional on mobile viewports.

#### Scenario: Mobile layout
- **WHEN** the viewport width is below 640px (sm breakpoint)
- **THEN** the modal MUST expand to full width with appropriate padding
- **AND** all form fields MUST stack vertically
- **AND** the BUY/SELL toggle MUST remain as a full-width segmented control

### Requirement: Replace PartialCloseModal
The `AddExecutionModal` SHALL replace the existing `PartialCloseModal` component entirely.

#### Scenario: PartialCloseModal removal
- **WHEN** the codebase is updated
- **THEN** `components/trades/PartialCloseModal.tsx` MUST be deleted
- **AND** all imports of `PartialCloseModal` MUST be replaced with `AddExecutionModal`
- **AND** the "Partial Close" button on the Trade Detail header MUST be removed (its functionality is covered by "+ Add Execution" with SELL selected)
