## ADDED Requirements

### Requirement: Aggregate Net PnL and Average Net Return
The `useReportData` hook SHALL compute and expose `netPnl` and `avgNetReturn` in its aggregated data objects (`PerformanceDataPoint`).

#### Scenario: Computing aggregated Net PnL
- **WHEN** filtering and aggregating a set of closed trades
- **THEN** `netPnl` equals the sum of `t.net_pnl` (or `t.pnl - t.commission` if `net_pnl` is unavailable)

#### Scenario: Computing Average Net Return
- **WHEN** evaluating average metrics for a subset of trades
- **THEN** `avgNetReturn` equals `netPnl / totalClosedTrades`