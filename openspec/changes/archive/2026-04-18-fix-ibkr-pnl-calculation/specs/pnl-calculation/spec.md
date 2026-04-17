## ADDED Requirements

### Requirement: Multiplier Attribute
The system SHALL store and expose a `multiplier` attribute (integer, default 1, minimum 1) for both raw broker transactions, logical executions, and aggregated trades.

#### Scenario: Trade Creation
- **WHEN** a trade is created (or updated) via the API
- **THEN** the system SHALL accept and validate a `multiplier` field
- **THEN** the system SHALL default to 1 if not provided

### Requirement: Dynamic Gross PnL Calculation
The system SHALL calculate the Gross PnL for a closed position dynamically based on execution prices, quantity, and contract multiplier, rather than relying on broker-provided aggregated PnL fields.

#### Scenario: Long Position Closed
- **WHEN** a closing execution matches an open long lot
- **THEN** the matched Gross PnL SHALL be calculated as `(Exit Price - Entry Price) * Match Quantity * Multiplier`

#### Scenario: Short Position Closed
- **WHEN** a closing execution matches an open short lot
- **THEN** the matched Gross PnL SHALL be calculated as `(Entry Price - Exit Price) * Match Quantity * Multiplier`

### Requirement: Dynamic Net PnL Calculation
The system SHALL calculate the Net PnL for a closed position by subtracting commissions from the dynamically calculated Gross PnL.

#### Scenario: Net PnL Deducts Commissions
- **WHEN** a closing execution matches an open lot
- **THEN** the matched Net PnL SHALL be calculated as `Gross PnL - (Matched Lot Commission + Matched Execution Commission)`
