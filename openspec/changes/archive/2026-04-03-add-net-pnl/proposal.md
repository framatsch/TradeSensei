## Why

Currently, the Trade Sensei only stores the gross PnL (`pnl`) and commissions separately. To accurately reflect a trader's performance, the Net PnL (gross PnL minus commissions) is the most critical metric. In the analysis views (like "Performance -> Time"), this net view is missing, and the table structure is currently flat, making it hard to read and compare gross vs. net performance at a glance.

## What Changes

- Add `net_pnl` and `net_pnl_eur` fields to the `Trade` database model and all related Pydantic schemas.
- Calculate `net_pnl` retroactively for all existing trades via an Alembic migration (`net_pnl = pnl - commission`).
- Update the frontend aggregation logic in `useReportData` to compute Total Net PnL and Avg Net Return.
- Redesign the table in `PerformanceAnalysisDashboard.tsx` to group metrics into four logical blocks: Overview (Volume), Profit & Loss, Win/Loss Metrics, and Averages.

## Capabilities

### New Capabilities

- `net-pnl-tracking`: Defines the requirements for storing and displaying net PnL across the application.
- `performance-table-layout`: Defines the structural layout and grouping of the performance analysis tables.

### Modified Capabilities

- `trade-metrics`: Modified to include net PnL and average net return in aggregations.

## Impact

- **Database:** `trades` table schema change and data migration.
- **Backend:** `Trade` SQLAlchemy model, `TradeCreate` / `TradeRead` Pydantic schemas, and parser aggregations.
- **Frontend:** `Trade` type definition, `useReportData` hook, and `PerformanceAnalysisDashboard` component.