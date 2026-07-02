## MODIFIED Requirements

### Requirement: Logical Execution Model
The system SHALL provide a mutable `LogicalExecution` table to store the application's view of executions, requiring a status flag indicating its lineage.

#### Scenario: Creating a logical execution
- **WHEN** a logical execution is created
- **THEN** it MUST contain a status flag chosen from: `imported`, `manual`, `merged`, `split`, or `open_position`

#### Scenario: open_position origin is valid
- **WHEN** a `LogicalExecution` is created with `origin = "open_position"`
- **THEN** the database CHECK constraint SHALL accept the record without error
