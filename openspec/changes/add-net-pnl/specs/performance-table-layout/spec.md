## ADDED Requirements

### Requirement: Structured Table Layout
The system SHALL present the performance analysis table in a structured format logically grouped into four primary categories: Overview, Profit & Loss, Win/Loss Metrics, and Averages.

#### Scenario: Visual grouping of columns
- **WHEN** the PerformanceAnalysisDashboard table renders
- **THEN** columns are arranged as: Name, Trades, Shares | Net P&L, Gross P&L, Commissions | Win %, Gross Win, Gross Loss, Profit Factor | Avg Net Return, Avg Gross Win, Avg Gross Loss

#### Scenario: Emphasizing Net P&L
- **WHEN** the Net P&L column renders
- **THEN** it receives strong visual emphasis (bold font or prominent text-success/text-danger colors) and sits directly beside Commissions for transparency