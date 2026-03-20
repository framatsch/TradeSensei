## ADDED Requirements

### Requirement: Include dividends in performance metrics
The system SHALL support aggregating dividend earnings into the total account performance metrics to reflect a true total return.

#### Scenario: Aggregate total dividends
- **WHEN** account metrics are calculated
- **THEN** the system also computes the total sum of `DIVIDEND` transactions minus `WITHHOLDING_TAX` to show net dividend income

#### Scenario: Display true total return
- **WHEN** the dashboard requests total performance
- **THEN** the system can return a "Total Return" that adds net trade PnL and net dividend income