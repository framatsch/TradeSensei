## ADDED Requirements

### Requirement: Dashboard displays monthly PnL chart
The system SHALL display a bar chart of PnL per calendar month on the dashboard,
sourced from `GET /timeseries/monthly-pnl`.

#### Scenario: Monthly PnL chart renders
- **WHEN** user opens the dashboard with at least one closed trade
- **THEN** a bar chart labelled "Monthly PnL" is visible showing monthly PnL bars

#### Scenario: Bars colour-coded by sign
- **WHEN** a month has positive PnL
- **THEN** that bar is green
- **WHEN** a month has negative PnL
- **THEN** that bar is red

#### Scenario: Tooltip shows details
- **WHEN** user hovers over a monthly bar
- **THEN** a tooltip shows PnL value, trade count, and win rate for that month

---

### Requirement: Dashboard displays return distribution histogram
The system SHALL display a histogram of trade PnL distribution on the dashboard,
sourced from `GET /timeseries/return-distribution`.

#### Scenario: Return distribution renders
- **WHEN** user opens the dashboard with at least 5 closed trades
- **THEN** a histogram labelled "Return Distribution" is visible

#### Scenario: Positive buckets green, negative buckets red
- **WHEN** a histogram bucket's midpoint is above zero
- **THEN** that bar is green; buckets below zero are red

#### Scenario: Tooltip shows bucket range and count
- **WHEN** user hovers over a histogram bar
- **THEN** a tooltip shows the PnL range and the count of trades in that bucket

---

### Requirement: Dashboard displays PnL by asset class chart
The system SHALL display a chart showing total PnL broken down by asset class
on the dashboard, sourced from `GET /timeseries/pnl-by-asset-class`.

#### Scenario: PnL by asset class renders
- **WHEN** user opens the dashboard with trades across multiple asset classes
- **THEN** a chart labelled "PnL by Asset Class" is visible

#### Scenario: Single asset class
- **WHEN** all trades belong to one asset class
- **THEN** the chart renders with a single entry

#### Scenario: Tooltip shows details
- **WHEN** user hovers over an asset class bar
- **THEN** a tooltip shows total PnL, trade count, and win rate for that asset class
