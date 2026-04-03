## Context

Currently, the `trades` table stores `pnl` (Gross PnL) and `commission`. While this preserves all raw data, the frontend only calculates and displays Gross PnL across most of its performance dashboards (e.g., Performance -> Time). To present a more accurate "Total PnL", the system needs to incorporate `net_pnl` as a first-class citizen. Additionally, the tabular view for these metrics is currently a flat list of 12 columns, making it difficult to digest.

## Goals / Non-Goals

**Goals:**
- Store `net_pnl` and `net_pnl_eur` as `Numeric(18, 4)` in the database to avoid rounding errors and repeated runtime calculations.
- Update existing trades via an Alembic migration to ensure historical data consistency.
- Restructure the `PerformanceAnalysisDashboard.tsx` table to group related metrics (Overview, P&L, Win/Loss, Averages).

**Non-Goals:**
- Renaming the existing `pnl` column to `gross_pnl` (this would introduce massive breaking changes across all API endpoints, schemas, and frontend queries).
- Changing the calculation of Profit Factor (it typically remains based on gross values, though this can be debated; for now, we leave it as is).

## Decisions

**Decision 1: Store `net_pnl` in the DB instead of calculating on-the-fly**
- **Rationale**: Since `pnl` is already stored in the DB, storing `net_pnl` keeps the API responses flat and performant. It also allows future database-level sorting and filtering (e.g., `net_pnl > 0`) without needing SQL math expressions in every query.
- **Alternatives Considered**: Calculate `net_pnl = pnl - commission` purely in the frontend or as a hybrid property in SQLAlchemy. We rejected this because filtering/sorting by Net PnL is a common database operation.

**Decision 2: Do not rename `pnl` to `gross_pnl`**
- **Rationale**: The column `pnl` is deeply ingrained in the application. Renaming it would break the OpenAPI schema, the frontend API client, and numerous frontend components. We will treat `pnl` as Gross PnL semantically, but keep the database column and JSON key as `pnl`.

**Decision 3: Redesign table with semantic groups**
- **Rationale**: The user requested a more functional layout. We will group the table headers visually:
  1. Overview: Name, Trades, Shares
  2. Profit & Loss: Net P&L, Gross P&L, Commissions
  3. Win/Loss: Win %, Gross Win, Gross Loss, Profit Factor
  4. Averages: Avg Net Return, Avg Gross Win, Avg Gross Loss

## Risks / Trade-offs

- **Risk**: During migration, trades without a `pnl` (open trades) might fail if we naively subtract `commission`.
  - **Mitigation**: The migration script must specifically target closed trades: `UPDATE trades SET net_pnl = pnl - commission WHERE pnl IS NOT NULL;`. Open trades will leave `net_pnl` as `NULL`.
- **Risk**: Double subtraction of commissions if a user manually inputs a net value into the gross `pnl` field.
  - **Mitigation**: We rely on the parser to extract the correct gross PnL. For manual inputs, the UI should clarify that the `pnl` field expects Gross PnL.