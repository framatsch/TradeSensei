## Context

The Portfolio Workspace is split across two disconnected routes: `/dashboard/analytics` (tab-based, legacy hooks, no lazy loading on tabs) and `/dashboard/reporting` (widget grid, lazy-loaded Recharts, filter bar). The sidebar nav has two separate inline sections (`AnalyticsNavSection`, `ReportingNavSection`) in the monolithic `layout.tsx`. Users experience browser freezes because the Analytics Hub mounts all 4 tab dashboards' Recharts components simultaneously on tab switch (static imports). The scatter widgets use mock data and have no safeguard against rendering thousands of DOM nodes.

**Existing assets to reuse (do not recreate):**
- All 7 chart widgets in `components/reporting/Widgets.tsx` — already lazy-loadable, already have skeletons
- Full calendar suite in `components/calendar/`
- `ReportFilterBar` with saved views
- All TanStack Query hooks in `hooks/useReportingAnalytics.ts` and `useReportData.ts`
- `components/reporting/ReportingSkeletons.tsx` and `EmptyState.tsx`

## Goals / Non-Goals

**Goals:**
- Unify analytics + reporting under `/dashboard/workspace/` with 5 isolated routes
- Guarantee lazy-loading of every Recharts component via `next/dynamic`
- Cache TanStack queries with `staleTime: 5min` so route navigation is instant
- Implement scatter circuit breaker (> 500 points → fallback, not render)
- Debounce filter bar and cancel stale requests
- Rename "Market Phase" → "Market Regime" in all UI labels
- Render "Uncategorized" for attribution widgets when check-in data is absent

**Non-Goals:**
- Backend API changes (no new endpoints)
- Rewriting Recharts chart implementations
- Changing the Trading Log or Check-in pillar layouts
- Implementing `/performance/time` or `/performance/risk` routes (Time and Risk tabs exist in analytics hub but are not in the workspace spec mockup)

## Decisions

### D1: Route structure — `/dashboard/workspace/` as new canonical base

**Decision:** Create `app/dashboard/workspace/` with a `layout.tsx` that renders the persistent workspace sidebar. The 5 routes map to: `overview/`, `calendar/`, `reporting/`, `performance/strategy/`, `performance/behavior/`.

**Alternatives considered:**
- Keep existing `/dashboard/analytics` + `/dashboard/reporting` and just fix performance: rejected because the fragmented structure is a root cause of the monolith problem and conflicts with the spec.
- Redirect-only (aliases to existing routes): rejected because it doesn't enable per-route code splitting or shared filter context.

**Rationale:** The `pillar-routing` spec defines `/dashboard/workspace/` as the canonical Portfolio Workspace path. Creating a clean `layout.tsx` here allows a `WorkspaceFilterContext` to be provided once to all child routes.

### D2: Global Filter State — React Context + URL search params

**Decision:** Create `components/workspace/WorkspaceFilterContext.tsx` that:
1. Reads initial state from URL search params (`?date_from`, `?date_to`, `?playbook_ids`, `?tag_ids`)
2. Provides the filter state + setter to all workspace child routes via context
3. Debounces URL writes (300ms) using `useDebounce`
4. Uses `useRouter` for URL updates (shallow push, no navigation)

**Alternatives considered:**
- Zustand store: adds a dependency, not needed for URL-synced state.
- Each route reads its own URL params: rejected because navigating between routes would lose filter state (Next.js unmounts context between route segments unless it's in a parent layout).

**Rationale:** Context in `workspace/layout.tsx` persists across all child routes. URL remains the source of truth for shareability/bookmarking.

### D3: Lazy Loading — `next/dynamic` per widget, not per page

**Decision:** Each Recharts-backed widget is `dynamic()` imported with `{ ssr: false, loading: () => <ChartSkeleton /> }` at the route file level. Non-chart components (MetricCard, text) are statically imported.

**Rationale:** This is already done correctly in the current reporting page. The analytics hub tabs need the same pattern applied. Per-widget granularity means only the rendered route's widgets are loaded.

### D4: TanStack Query caching — `staleTime: 5 * 60 * 1000`

**Decision:** Add `staleTime: 5 * 60 * 1000` (5 minutes) to all hooks in `useReportingAnalytics.ts` and `useReportData.ts`. Query keys must include a serialized `filter_config` object (already used as `JSON.stringify(filterConfig)` in some hooks — standardize this).

**Rationale:** A 5-minute stale time means route navigation with unchanged filters never triggers a network request or remounts skeletons, giving the appearance of instant navigation.

### D5: Scatter Circuit Breaker — data-length guard before render

**Decision:** In `MaeMfeScatterWidget` and `DurationVsPnlScatterWidget`, check `data.length > 500` before rendering the `ScatterChart`. If true, render a `<FallbackPrompt>` component instructing the user to narrow their date range or filter. The threshold (500) is exported as a constant `SCATTER_MAX_RAW_POINTS`.

**Rationale:** The backend does not yet guarantee hexbin clustering for all query sizes. A frontend guard prevents the known freeze scenario. The threshold is a tunable constant so it can be raised once server-side clustering is confirmed.

### D6: Sidebar — extract `WorkspaceSidebarNav` from `layout.tsx`

**Decision:** Create `components/workspace/WorkspaceSidebarNav.tsx` as a standalone component. `app/dashboard/workspace/layout.tsx` renders it alongside the main content slot. The global `app/dashboard/layout.tsx` keeps its existing nav items for non-workspace routes but the workspace layout overrides the sidebar slot.

**Rationale:** The monolithic `layout.tsx` is 615 lines. Extracting the workspace nav reduces its complexity and makes the workspace section independently testable.

### D7: "Market Phase" → "Market Regime" renaming

**Decision:** Rename only UI-facing display strings (labels, headings, legend text). Do NOT rename TypeScript type names, API field names, or hook names that reference backend `market_phase` fields — those are backend-owned and would require a separate API migration.

**Rationale:** Cosmetic rename only avoids breaking the generated API client types.

## Risks / Trade-offs

- **[Risk] `/dashboard/analytics` becomes orphaned** → Mitigation: Add a redirect from `/dashboard/analytics` → `/dashboard/workspace/performance/strategy` (the most equivalent route). `/dashboard/reporting` → `/dashboard/workspace/reporting`.
- **[Risk] Filter context re-renders all workspace routes on every filter change** → Mitigation: Wrap expensive computations in `useMemo`; child components use `React.memo` where appropriate.
- **[Risk] `useScatterAnalytics` still uses mock data** → Mitigation: Keep mock data with the circuit breaker applied. When the real endpoint ships, swap the mock with a real hook call — the circuit breaker logic stays unchanged.
- **[Risk] Sidebar nav breakage for users without `reporting_hub` feature flag** → Mitigation: Wrap workspace sidebar items with the same feature flag check already used in `buildNavItems()`.

## Migration Plan

1. Create `app/dashboard/workspace/` routes and layout (no changes to existing routes)
2. Update sidebar in `app/dashboard/layout.tsx` to include workspace nav items pointing to new paths
3. Add redirects from `/dashboard/analytics` and `/dashboard/reporting` → workspace equivalents
4. Apply performance fixes (staleTime, circuit breaker, debounce) to existing hooks/components
5. Rename Market Phase → Market Regime in display strings
6. Fix Uncategorized attribution rendering
7. Remove or deprecate `app/dashboard/analytics/` tab files (can be deferred — redirects cover users)

**Rollback:** Redirects can be removed; old routes remain functional throughout migration.

## Open Questions

- Should `/performance/time` and `/performance/risk` routes be stubs (404 or "Coming Soon") or omitted entirely from the sidebar?
- Should the `/dashboard/reports/` route subtree be removed or just redirected?
