## ADDED Requirements

### Requirement: Backend exposes rolling winrate endpoint
The system SHALL provide a `GET /timeseries/rolling-winrate` endpoint that
returns per-trade rolling win rate computed over the last N closed trades.

Parameters:
- `window_trades` (int, default 20, min 5, max 100): number of trades in the rolling window
- `account_id` (UUID, optional): filter to one account
- `from_dt` / `to_dt` (datetime, optional): date range filter

Response items:
- `trade_index` (int): 1-based sequential index of the trade
- `closed_at` (datetime): when the trade was closed
- `rolling_winrate` (Decimal): fraction of wins in the last `window_trades` trades (0.0–1.0)
- `window` (int): actual window size used (may be smaller than requested for early trades)

#### Scenario: Rolling winrate with default window
- **WHEN** client calls `GET /timeseries/rolling-winrate` with no parameters
- **THEN** the response contains one item per closed trade with `rolling_winrate` computed over the last 20 trades

#### Scenario: Custom window size
- **WHEN** client calls with `window_trades=50`
- **THEN** each item uses a 50-trade window

#### Scenario: Window smaller than available trades
- **WHEN** there are fewer trades than the window size
- **THEN** `window` reflects the actual number of trades used and `rolling_winrate` is still returned

#### Scenario: No closed trades
- **WHEN** the user has no closed trades
- **THEN** the endpoint returns an empty array with HTTP 200

---

### Requirement: Dashboard displays rolling winrate chart
The system SHALL display a line chart of rolling win rate (over last N trades)
on the dashboard, sourced from `GET /timeseries/rolling-winrate`.

#### Scenario: Rolling winrate chart renders
- **WHEN** user opens the dashboard with at least 5 closed trades
- **THEN** a line chart labelled "Rolling Win Rate" is visible

#### Scenario: Window selector
- **WHEN** user changes the window size selector (10 / 20 / 50 trades)
- **THEN** the chart re-fetches and updates to reflect the new window

#### Scenario: Reference line at 50%
- **WHEN** the chart renders
- **THEN** a dashed horizontal reference line at 0.5 (50% win rate) is visible

#### Scenario: Tooltip shows date and winrate
- **WHEN** user hovers over the chart line
- **THEN** a tooltip shows the trade's close date and the rolling win rate as a percentage

---

### Requirement: Dashboard displays monthly winrate chart
The system SHALL display a bar chart of win rate per calendar month on the
dashboard, derived from the existing `GET /timeseries/monthly-pnl` endpoint.

#### Scenario: Monthly winrate bars render
- **WHEN** user opens the dashboard with at least one month of closed trades
- **THEN** a bar chart labelled "Monthly Win Rate" is visible with one bar per month

#### Scenario: 50% reference line present
- **WHEN** the chart renders
- **THEN** a dashed horizontal reference line at 50% win rate is shown

#### Scenario: Tooltip shows month and details
- **WHEN** user hovers over a monthly bar
- **THEN** a tooltip shows the month label, win rate percentage, and trade count
