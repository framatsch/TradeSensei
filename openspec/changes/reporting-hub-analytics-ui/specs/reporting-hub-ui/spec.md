## ADDED Requirements

### Requirement: Hierarchical UI Layout
The system SHALL render the Reporting Hub with three main sections: 1) View Management, 2) Global Filters Panel (collapsible), and 3) Reactive Widget Grid.

#### Scenario: Page Initialization
- **WHEN** the user navigates to the Reporting Hub
- **THEN** the View Management, Global Filters, and Widget Grid are visible in a top-down hierarchy.

### Requirement: Performance Classic Widgets
The system SHALL display "Performance Classic" widgets including an Equity Curve (Net P&L), Drawdown Curve (Relative), and R-Multiple Distribution (Histogram).

#### Scenario: Display Equity Curve
- **WHEN** the Widget Grid loads with valid data
- **THEN** an Equity Curve chart is rendered showing the cumulative Net P&L over time.

### Requirement: Key Metrics Widgets
The system SHALL display "Key Metrics" widgets showing Win Rate, Profit Factor, and Payoff Ratio (Average Win vs. Average Loss in $ and R).

#### Scenario: Display Profit Factor
- **WHEN** the Widget Grid loads with valid data
- **THEN** a numeric display for Profit Factor is rendered.

### Requirement: Execution Analysis Widgets
The system SHALL display "Execution Analysis" widgets including MAE/MFE Scatterplot and Time-in-Trade vs. P&L Scatterplot.

#### Scenario: Display Scatterplots
- **WHEN** the Widget Grid loads with valid data
- **THEN** the MAE/MFE and Duration vs. P&L scatterplots are rendered.

### Requirement: Attribution Widgets
The system SHALL display "Attribution" widgets including a Heatmap (Playbook vs. Market Phase) and a Bar Chart (Custom Check-in Metrics like Focus Level vs. Average R-Multiple).

#### Scenario: Missing Check-in Attribution
- **WHEN** trades exist without a corresponding daily check-in
- **THEN** the Attribution Heatmap displays these trades aggregated in an explicit "Uncategorized / No Context" column or row, rather than omitting them.

### Requirement: Loading Skeletons
The system SHALL display loading skeletons for widgets while analytical backend queries are in progress.

#### Scenario: Slow Backend Response
- **WHEN** the user changes a filter and the API request is pending
- **THEN** the affected widgets display a loading skeleton layout that prevents layout shift.

### Requirement: Empty States
The system SHALL display explicit empty states when no data is returned for the selected filter combination.

#### Scenario: Zero Trades Matching
- **WHEN** the API returns an empty dataset for the current filters
- **THEN** all widgets display an explicit empty state message (e.g., "No trades match the current filters") instead of rendering empty charts or crashing.

### Requirement: Playwright UI Testing
The frontend SHALL include automated Playwright UI tests for the Reporting Hub covering layouts, interactions, loading states, and empty states.

#### Scenario: Empty State Test Execution
- **WHEN** the UI tests run
- **THEN** a test validates that the empty state is correctly rendered when a filter combination yields no results.
