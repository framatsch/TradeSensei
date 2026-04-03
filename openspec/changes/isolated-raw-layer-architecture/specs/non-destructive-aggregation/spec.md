## ADDED Requirements

### Requirement: Logical Aggregation
The aggregator (`aggregator.py`) MUST perform calculations and FIFO-matching exclusively based on the `LogicalExecution` table.

#### Scenario: Non-destructive Commission Splitting
- **WHEN** executions are matched
- **THEN** the proportional allocation of commissions MUST occur exclusively on the logical layer.

### Requirement: Dynamic Corporate Actions
The system MUST apply stock splits dynamically on the logical layer.

#### Scenario: Stock Split Handling
- **WHEN** a corporate action event (split) is processed
- **THEN** the origin data for quantities and prices in `BrokerRawTransaction` MUST NOT be modified.

### Requirement: Validation & Conflict Resolution
The system MUST NOT perform automatic closures when there are discrepancies between application logic and broker data.

#### Scenario: Open Position Mismatch
- **WHEN** the summed quantity of `LogicalExecution` entries does not match the XML block `<OpenPosition>`
- **THEN** the system MUST set the `has_conflict` flag on the affected `Trade` and MUST NOT execute a `force-closed` with 0 PnL.
