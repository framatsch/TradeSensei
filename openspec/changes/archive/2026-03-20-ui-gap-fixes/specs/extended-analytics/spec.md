## ADDED Requirements

### Requirement: Dashboard shows monthly PnL bar chart
The dashboard SHALL include a bar chart of monthly PnL, consuming the `/timeseries/monthly-pnl` endpoint, placed in a second analytics row below the equity/drawdown charts.

#### Scenario: Monthly PnL chart renders
- **WHEN** user views the dashboard
- **THEN** a bar chart labeled "Monthly PnL" is visible with one bar per calendar month
- **AND** bars are colored green for positive months and red for negative months

#### Scenario: Empty state
- **WHEN** there are no closed trades
- **THEN** the chart area shows "No data yet" placeholder text

### Requirement: Dashboard shows PnL by symbol chart
The dashboard SHALL display the existing `PnlBySymbolChart` component, consuming `/timeseries/pnl-by-symbol`, in the second analytics row.

#### Scenario: PnL by symbol chart renders
- **WHEN** user views the dashboard with at least one closed trade
- **THEN** a chart showing PnL grouped by symbol is visible

### Requirement: Dashboard shows PnL by asset class chart
The dashboard SHALL include a chart for PnL broken down by asset class, consuming `/timeseries/pnl-by-asset-class`.

#### Scenario: Asset class chart renders
- **WHEN** user views the dashboard
- **THEN** a chart showing PnL per asset class (EQUITY, OPTION, etc.) is visible

### Requirement: Dashboard shows return distribution histogram
The dashboard SHALL include a histogram of trade returns, consuming `/timeseries/return-distribution`.

#### Scenario: Return distribution renders
- **WHEN** user views the dashboard with at least 5 closed trades
- **THEN** a histogram of return values is visible, showing the frequency distribution of individual trade PnLs
