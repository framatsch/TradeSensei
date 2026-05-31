## ADDED Requirements

### Requirement: Configure Chart Intervals
The system SHALL allow users to select which chart intervals are supported and visible in the Trade Chart UI. The allowed options are "1h", "4h", and "1d".

#### Scenario: User saves chart intervals
- **WHEN** user selects specific intervals in the Settings UI and clicks save
- **THEN** the backend updates the `chart_intervals` list for the user
- **THEN** the frontend caches the new intervals and applies them to `TradeChart`

#### Scenario: TradeChart renders configured intervals
- **WHEN** the TradeChart component renders
- **THEN** it displays interval selection buttons only for the timeframes listed in `chart_intervals`
- **THEN** it selects the most granular available interval as the default based on the trade's duration

#### Scenario: At least one interval is required
- **WHEN** user attempts to deselect all intervals in settings
- **THEN** the UI prevents saving and shows a validation error or automatically ensures at least "1d" is kept selected
