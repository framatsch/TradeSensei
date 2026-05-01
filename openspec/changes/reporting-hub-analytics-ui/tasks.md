## 1. Setup & State Management

- [x] 1.1 Scaffold the Reporting Hub page (`app/dashboard/reporting/page.tsx`) with a basic 3-part layout (View Management, Filters, Grid).
- [x] 1.2 Implement the URL-based state management structure for filters using Next.js search parameters.
- [x] 1.3 Create the global filter UI components (Date Range, Playbooks, Tags).
- [x] 1.4 Implement the Single Portfolio selection logic (enforcing exactly one portfolio) and the Trade Status toggle (defaulting to Closed Only).

## 2. API Integration & View Management

- [x] 2.1 Integrate TanStack Query for data fetching, connecting to the existing Analytics API (`POST /api/v1/portfolios/{portfolio_id}/analytics/summary`), Attribution API (`GET /api/v1/portfolios/{portfolio_id}/analytics/correlations/market-phase`), and SavedDashboardView API (`/api/v1/portfolios/{portfolio_id}/views`).
- [x] 2.2 Create custom hooks for fetching aggregated metrics, performance data, and scatterplot data.
- [x] 2.3 Implement the "Save View" functionality using `POST /api/v1/portfolios/{portfolio_id}/views` to persist current filter parameters as named views, and `GET /api/v1/portfolios/{portfolio_id}/views` to populate the view management dropdown.
- [x] 2.4 Add debouncing to filter changes to prevent excessive API requests.

## 3. UI Components & Skeletons

- [x] 3.1 Create loading skeleton components for Performance Classic widgets, Key Metrics, Execution Scatterplots, and Attribution tables.
- [x] 3.2 Create explicit Empty State components (e.g., "No trades found for these filters").
- [x] 3.3 Implement the View Management UI component to switch between saved views.

## 4. Charts & Widgets

- [x] 4.1 Implement "Performance Classic" widgets using Recharts: Equity Curve, Drawdown Curve, and R-Multiple Distribution.
- [x] 4.2 Implement "Key Metrics" widgets: Win Rate, Profit Factor, Payoff Ratio displays.
- [x] 4.3 Implement "Execution Analysis" widgets: MAE/MFE Scatterplot and Duration vs. P&L Scatterplot, handling server-side hexbin data format if > 500 points.
- [x] 4.4 Implement "Attribution" widgets: Playbook vs. Market Phase Heatmap and Psychological Attribution Bar Chart.
- [x] 4.5 Ensure "Uncategorized / No Context" data is properly rendered in the Attribution widgets.

## 5. UI Testing

- [x] 5.1 Write Playwright UI tests for the Reporting Hub initial layout and View Management.
- [x] 5.2 Write Playwright tests to verify the Single Portfolio filter enforcement and Trade Status toggle default state.
- [x] 5.3 Write Playwright tests covering the Empty State display when no data matches filters.
- [x] 5.4 Write Playwright tests verifying the visibility of Loading Skeletons during data fetching delays.
