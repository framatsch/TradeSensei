## ADDED Requirements

### Requirement: Read-Only Computed Fields in Edit Form
The `TradeEditForm` SHALL render execution-derived fields as read-only when the trade has `LogicalExecution` records.

#### Scenario: Computed fields are non-editable
- **WHEN** the user opens the Edit Trade form for a trade with execution legs
- **THEN** the following fields MUST be rendered as read-only (disabled inputs with a lock icon): Quantity, Entry Price, Exit Price, PnL, Commission
- **AND** each read-only field MUST display a "Computed from executions" hint
- **AND** a link MUST be provided to navigate to the Execution Legs section ("Edit individual executions in the Execution Legs section above")

#### Scenario: Computed timestamps
- **WHEN** the trade has execution legs
- **THEN** Opened At MUST be read-only (derived from the earliest execution's `executed_at`)
- **AND** Closed At MUST be read-only (derived from the latest closing execution's `executed_at`, or null if open)

### Requirement: Editable Metadata Fields
The `TradeEditForm` SHALL keep metadata fields fully editable regardless of execution presence.

#### Scenario: Editable metadata fields
- **WHEN** the user opens the Edit Trade form
- **THEN** the following fields MUST remain editable: Symbol, Direction, Asset Class, Currency, Stop Loss, Take Profit, Playbook, Tags, Notes, TradingView Link

### Requirement: Read-Only Visual Style
Read-only computed fields SHALL be visually distinct from editable fields.

#### Scenario: Visual differentiation
- **WHEN** the Edit Form renders a read-only computed field
- **THEN** the input MUST have a lighter background (`bg-secondary/50`)
- **AND** the input MUST display a lock icon (🔒 or padlock SVG)
- **AND** the input MUST be disabled (not focusable, no cursor)
- **AND** the label MUST include a "Computed" indicator

### Requirement: Manual Trade Edit Fallback
For trades created manually without any `LogicalExecution` records, the Edit Form SHALL remain fully editable.

#### Scenario: Full edit for execution-less trades
- **WHEN** a user opens the Edit Form for a trade with zero execution legs
- **THEN** all fields MUST remain editable (same behavior as current)
- **AND** no "Computed from executions" hints MUST be shown

### Requirement: Auto-Create Execution on Manual Trade Creation
When a trade is created via the "New Trade" form, the backend SHALL automatically create a corresponding `LogicalExecution` with `status: manual`.

#### Scenario: New trade gets an execution
- **WHEN** a user creates a trade via `POST /api/v1/trades` with entry_price, quantity, and opened_at
- **THEN** the backend MUST create a `LogicalExecution` with the trade's entry values and `status: manual`
- **AND** the execution MUST be assigned to the newly created trade

### Requirement: TradeEditForm Payload Reduction
The `TradeEditForm` SHALL exclude computed fields from its update payload when the trade has execution legs.

#### Scenario: Payload excludes computed fields
- **WHEN** the user saves the Edit Form for a trade with execution legs
- **THEN** the `TradeUpdate` payload MUST NOT include: `quantity`, `entry_price`, `exit_price`, `pnl`, `commission`, `opened_at`, `closed_at`
- **AND** only metadata fields changed by the user MUST be sent
