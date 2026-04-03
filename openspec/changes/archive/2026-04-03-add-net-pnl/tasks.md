## 1. Backend Data Model & Migrations

- [x] 1.1 Update `app/models/trade.py`: Add `net_pnl` and `net_pnl_eur` as `Numeric(18, 4)` columns to the `Trade` model.
- [x] 1.2 Update `app/schemas/trade.py`: Add `net_pnl` and `net_pnl_eur` to `TradeCreate`, `TradeCreateRequest`, `TradeUpdate`, and `TradeRead`.
- [x] 1.3 Create an Alembic migration (`uv run alembic revision -m "add net_pnl"`) that adds the new columns and updates existing closed trades: `UPDATE trades SET net_pnl = pnl - commission WHERE pnl IS NOT NULL`.
- [x] 1.4 Update `app/utils/parsers/aggregator.py` to calculate and assign `net_pnl` and `net_pnl_eur` when setting `pnl` and `pnl_eur` for closed trades.
- [x] 1.5 Update backend tests and run `uv run pytest tests/` and `python tools/lint_check.py --ci` to ensure everything passes.

## 2. Frontend Types & Aggregation Hooks

- [x] 2.1 Update `frontend/lib/types.ts` to include `net_pnl` and `net_pnl_eur` in the `Trade` interface.
- [x] 2.2 Update `frontend/components/trades/PerformanceAnalysisDashboard.tsx`: Add `netPnl` and `avgNetReturn` to the `PerformanceDataPoint` interface.
- [x] 2.3 Update `frontend/hooks/useReportData.ts`: Modify the aggregation logic to compute `netPnl` (sum of `t.net_pnl` or `t.pnl - t.commission`) and `avgNetReturn` (`netPnl / totalTrades`).

## 3. Frontend UI (Table Redesign)

- [x] 3.1 Open `frontend/components/trades/PerformanceAnalysisDashboard.tsx` and redesign the `<thead>` to visually group columns: Overview, Profit & Loss, Win/Loss, Averages.
- [x] 3.2 Reorder the `<td>` elements in the `<tbody>` to match the new header order: Name, Trades, Shares, Net P&L, Gross P&L, Commissions, Win %, Gross Win, Gross Loss, Profit Factor, Avg Net Return, Avg Gross Win, Avg Gross Loss.
- [x] 3.3 Apply typography and color styling to emphasize `Net P&L` and visually distinguish the groups.
- [x] 3.4 Run `npx tsc --noEmit` and check the UI in the browser to ensure the layout looks correct and is functionally sound.