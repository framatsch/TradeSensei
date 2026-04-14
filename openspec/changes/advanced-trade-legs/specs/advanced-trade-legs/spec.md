## ADDED Requirements

### Requirement: Advanced Manual Trade Legs
The system SHALL allow users to create trades with multiple manual execution legs, bypassing auto-generation.

#### Scenario: Creating a trade with manual legs
- **WHEN** a user submits a POST request to `/api/v1/trades` with the `executions` array populated
- **THEN** the system creates the trade and associates the provided `executions` as `LogicalExecution` records
- **AND** the system DOES NOT auto-generate entry or exit executions

#### Scenario: Creating a trade without manual legs
- **WHEN** a user submits a POST request to `/api/v1/trades` with `executions` set to null or omitted
- **THEN** the system creates the trade and auto-generates 1 or 2 `LogicalExecution` records based on `entry_price` and `exit_price`

### Requirement: Progressive Disclosure UI
The frontend trade creation form SHALL provide an "Advanced" mode toggle for manually entering execution legs.

#### Scenario: Switching to Advanced mode
- **WHEN** the user toggles the form from "Basic" to "Advanced" mode
- **THEN** the top-level inputs for `quantity`, `entry_price`, and `exit_price` become read-only
- **AND** a dynamic list of execution legs appears

#### Scenario: Adding manual legs
- **WHEN** the user is in "Advanced" mode and adds a new execution leg with quantity and price
- **THEN** the top-level read-only inputs for `quantity` and `entry_price`/`exit_price` are automatically recalculated and updated in the UI

#### Scenario: Submitting Advanced mode trade
- **WHEN** the user submits the form in "Advanced" mode
- **THEN** the payload includes the `executions` array containing the user's manual legs
