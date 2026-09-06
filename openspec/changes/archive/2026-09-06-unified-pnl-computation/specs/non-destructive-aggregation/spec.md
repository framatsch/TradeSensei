## ADDED Requirements

### Requirement: Re-Aggregation Is Equivalent To Import
Re-aggregating an existing `Trade` from its `LogicalExecution` rows MUST produce the same
derived values that importing those same executions would produce. The FIFO aggregator is
the reference implementation; any other path that recomputes a trade from its executions
MUST follow it.

#### Scenario: Same Executions Yield Same PnL
- **WHEN** a trade is re-aggregated from a set of executions
- **THEN** the resulting `pnl`, `net_pnl`, `entry_price`, `exit_price`, `quantity` and `commission` MUST equal the values that `aggregate_executions_fifo` produces for the same executions

#### Scenario: Editing A Leg Does Not Change An Untouched Result
- **WHEN** a trade is re-aggregated without any of its executions having changed
- **THEN** the trade's derived values MUST be unchanged

#### Scenario: Re-Aggregation Is Idempotent
- **WHEN** a trade is re-aggregated twice in succession with no intervening change
- **THEN** the second re-aggregation MUST produce the same values as the first

### Requirement: Every Trade Mutation Path Preserves PnL Correctness
Every path that mutates executions or trades MUST leave the affected trades' PnL consistent
with the `pnl-calculation` capability. This covers creating, updating, deleting, splitting,
merging, reassigning and restoring an execution, merging trades, and replaying corporate
actions.

#### Scenario: Merging Two Trades
- **WHEN** two closed trades of the same instrument and direction are merged
- **THEN** the surviving trade's `pnl` MUST be derived from the combined executions' prices
- **AND** MUST NOT be zero solely because the underlying broker reports no realised PnL

#### Scenario: Corporate Action Replay
- **WHEN** a corporate action is applied or removed and affected trades are re-aggregated
- **THEN** the recomputed PnL MUST follow the split-adjusted execution prices
