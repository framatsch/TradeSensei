## ADDED Requirements

### Requirement: Integration Testing & Verification
The system MUST prove the mathematical correctness of the new architecture via integration tests.

#### Scenario: PnL Baseline Validation
- **WHEN** the automated integration test is executed with historical XML files
- **THEN** the aggregated PnL in the database (filtered by imported executions and `closed_at` on a yearly basis) MUST exactly match the output of the `flex_query_aggregation.py` script.

### Requirement: Ground-Truth Generator Script
The system SHALL provide a `flex_query_aggregation.py` script to parse IBKR XML flex queries and generate the ground-truth database PnL, factoring in commissions, `TransactionTax`, and `CashTransaction` items (FEE category).

#### Scenario: Running the ground-truth generator
- **WHEN** the script is executed against historical XML files
- **THEN** it SHALL calculate commissions using `max(abs(ibCommission), abs(commission))` and subtract taxes and fees from the net performance.
