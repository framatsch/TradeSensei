## MODIFIED Requirements

### Requirement: Logical Execution Model
The system SHALL provide a mutable `LogicalExecution` table to store the application's view of executions, requiring a status flag indicating its lineage. The `open_position` origin SHALL be a broker-neutral value available to any broker adapter that seeds open lots from position snapshots, not specific to a single broker.

#### Scenario: Creating a logical execution
- **WHEN** a logical execution is created
- **THEN** it MUST contain a status flag chosen from: `imported`, `manual`, `merged`, `split`, or `open_position`

#### Scenario: open_position origin is valid
- **WHEN** a `LogicalExecution` is created with `origin = "open_position"`
- **THEN** the database CHECK constraint SHALL accept the record without error

#### Scenario: open_position origin is broker-neutral
- **WHEN** a broker adapter (e.g. IBKR or Schwab) seeds an open lot from a position snapshot
- **THEN** it SHALL use the shared `origin = "open_position"` value
- **THEN** no broker-specific origin value SHALL be introduced for open positions
