## Context

The Reporting Hub frontend requires complex state management and handles significant data processing tasks (like server-side hexbinning) initiated via API requests. Since no client-side mathematical aggregations are allowed, the architecture must efficiently manage state, loading states (Skeletons) for long-running queries, and explicit empty states. Additionally, comprehensive Playwright UI tests must be included to verify layout, interactions, and fallback scenarios.

## Goals / Non-Goals

**Goals:**
- Create a robust frontend state management system for global filters, enforcing rules (e.g., exactly one portfolio/base currency).
- Implement responsive UI components for the widget grid, including loading skeletons and explicit empty states.
- Ensure performant visualization rendering using Recharts, delegating aggregations/clustering to the backend API.
- Cover all new components with Playwright UI tests matching the provided mockups and project UI standards.

**Non-Goals:**
- Client-side data aggregation or math beyond simple formatting.

## Decisions

- **State Management**: Use URL search parameters combined with a lightweight store (e.g., React Context or Zustand) to manage View Management state. Views are persisted server-side via `POST/GET /api/v1/portfolios/{portfolio_id}/views` (SavedDashboardView API). The active `view_id` is reflected in URL search params, making views shareable via URL.
- **Data Fetching**: Use TanStack Query (React Query) to fetch data. Its built-in `isLoading`, `isError`, and `data` states map perfectly to our requirements for Loading Skeletons and Empty States.
- **Charts**: Use `recharts` for visualizations (Performance Classic, MAE/MFE Scatterplot, Attribution). For scatterplots, the component will observe the data format returned by the API; if the backend returns clustered/hexbin data for >500 points, the chart will render accordingly.
- **Loading Skeletons**: Implement bespoke skeleton components that mirror the layout of the widgets to prevent cumulative layout shift (CLS) during long-running analytical queries.
- **Testing**: Playwright for end-to-end UI tests, specifically testing for empty states (e.g., no trades matching filters) and validating the exact single-portfolio constraint.

## Risks / Trade-offs

- **Risk: Long-running backend queries causing perceived sluggishness.** -> *Mitigation*: Extensive use of Suspense boundaries and specialized Loading Skeletons for each widget type, along with debounced filter inputs to avoid overwhelming the API.
- **Risk: Scatterplot rendering crashing the browser with too many DOM nodes.** -> *Mitigation*: Strictly enforce the rule that > 500 data points triggers server-side hexbinning. The frontend will defensively limit rendering if the backend accidentally sends raw points.
- **Risk: Filter state inconsistencies.** -> *Mitigation*: Implement rigorous validation logic in the state management layer (e.g., preventing deselecting the last portfolio). UI tests must specifically cover these edge cases.