## ADDED Requirements

### Requirement: Database storage of Net PnL
The system SHALL store the net profit and loss (`net_pnl`) and its EUR equivalent (`net_pnl_eur`) for each trade in the database.

#### Scenario: Trade close calculation
- **WHEN** a trade is closed and a gross `pnl` is calculated
- **THEN** the system computes `net_pnl = pnl - commission` and persists it to the database

#### Scenario: Open trade handling
- **WHEN** a trade remains open (i.e., `pnl` is NULL)
- **THEN** the system leaves `net_pnl` as NULL

### Requirement: Historical data migration
The system SHALL retroactively calculate and populate the `net_pnl` and `net_pnl_eur` fields for all existing closed trades.

#### Scenario: Apply alembic migration
- **WHEN** the Alembic migration runs
- **THEN** all rows with a non-null `pnl` receive a `net_pnl` value equal to `pnl - commission`