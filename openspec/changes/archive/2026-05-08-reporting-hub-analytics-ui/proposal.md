## Why

The system strictly separates operational trade recording from analytical evaluation. We currently lack a comprehensive frontend interface to access the analytical layer (Analytics API) and attribution data (Attribution API). This change implements the Reporting Hub & Analytics UI (Frontend) to allow traders to visualize performance metrics, analyze execution statistics, and correlate trades with daily check-ins and psychological states.

## What Changes

- Implementation of the Reporting Hub frontend page with a hierarchical structure: View Management, Global Filters, and a Reactive Widget Grid.
- Addition of a state management solution for handling complex filtering, including strict business rules (e.g., forcing a single portfolio/base currency, toggling open trades).
- Integration with existing Analytics API and Attribution API endpoints.
- Implementation of dynamic, data-heavy widgets such as Equity Curves, Drawdowns, R-Multiple Distributions, Key Metrics, Scatterplots (with server-side hexbinning for >500 trades), and Attribution Heatmaps/Bar Charts.
- Implementation of comprehensive UI tests based on UI mockups and application UI standards.
- Addition of robust UX patterns including loading skeletons for long-running analytic queries and explicit empty states for zero-trade filter results.

## Capabilities

### New Capabilities
- `reporting-hub-ui`: The frontend Reporting Hub interface including view management, global filters, and the reactive widget grid with various charts and metrics.
- `reporting-hub-filters`: Complex state management and business rules for reporting filters (portfolio selection, trade status toggles, date ranges, missing data handling).

### Modified Capabilities
- None

## Impact

- Frontend application (Next.js) will receive new pages, components, and state management logic.
- UI Testing suite (Playwright) will be expanded with tests for the Reporting Hub features, ensuring visual and functional correctness.
- Relies on the Analytics and Attribution APIs to handle heavy calculations and clustering/hexbinning requests.