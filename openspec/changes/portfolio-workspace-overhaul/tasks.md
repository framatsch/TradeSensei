## 1. Codebase Audit & Delta Confirmation

- [ ] 1.1 Verify existing lazy-loading in `app/dashboard/reporting/page.tsx` (dynamic imports for all 7 widgets) — document which are missing
- [ ] 1.2 Audit `app/dashboard/analytics/` tab files for static Recharts imports — list which need `next/dynamic` wrappers
- [ ] 1.3 Audit `hooks/useReportingAnalytics.ts` and `hooks/useReportData.ts` for missing `staleTime` and unstable query keys
- [ ] 1.4 Confirm `useScatterAnalytics` is mock data — note the point count returned and verify circuit breaker is absent

## 2. Global Filter Context & URL Sync

- [ ] 2.1 Create `components/workspace/WorkspaceFilterContext.tsx` — defines `FilterConfig` type, reads initial state from URL params, provides context with setter
- [ ] 2.2 Implement 300ms debounce on URL writes in `WorkspaceFilterContext` using `useEffect` + `setTimeout` / `useDebounce`
- [ ] 2.3 Add `AbortController`-based request cancellation to `useAnalyticsSummary` and `useReportData` hooks (pass signal to API calls)

## 3. TanStack Query Performance

- [ ] 3.1 Add `staleTime: 5 * 60 * 1000` to all hooks in `hooks/useReportingAnalytics.ts`
- [ ] 3.2 Standardize query keys in `useReportingAnalytics.ts` to include `JSON.stringify(filterConfig)` as a stable key segment
- [ ] 3.3 Add `staleTime: 5 * 60 * 1000` and stable filter-based keys to `hooks/useReportData.ts`

## 4. Scatter Circuit Breaker

- [ ] 4.1 Add `export const SCATTER_MAX_RAW_POINTS = 500` constant to `components/reporting/Widgets.tsx`
- [ ] 4.2 Implement circuit breaker in `MaeMfeScatterWidget` — check `data.length > SCATTER_MAX_RAW_POINTS` before rendering `ScatterChart`, show fallback UI if exceeded
- [ ] 4.3 Implement circuit breaker in `DurationVsPnlScatterWidget` — same pattern as 4.2

## 5. Attribution Widget Fixes

- [ ] 5.1 Update `PsychologicalAttributionWidget` to group trades without check-in data under an "Uncategorized" entry rather than omitting them
- [ ] 5.2 Update `PlaybookPhaseHeatmapWidget` to render an "Uncategorized" row for trades without check-in data
- [ ] 5.3 Rename all display strings "Market Phase" → "Market Regime" in `PsychologicalAttributionWidget` (labels, headings, tooltips)
- [ ] 5.4 Rename all display strings "Market Phase" → "Market Regime" in `PlaybookPhaseHeatmapWidget`

## 6. Workspace Sidebar Nav Component

- [ ] 6.1 Create `components/workspace/WorkspaceSidebarNav.tsx` — renders ANALYTICS (Overview, Calendar), REPORTING (Reporting Hub + saved view sub-links), PERFORMANCE (Strategy, Behavior) sections
- [ ] 6.2 Wire saved view sub-links in `WorkspaceSidebarNav` using existing `useSavedViews` hook — link to `/dashboard/workspace/reporting?view_id=<id>`
- [ ] 6.3 Implement active route highlight in `WorkspaceSidebarNav` using `usePathname()`

## 7. Workspace Layout & Route Scaffolding

- [ ] 7.1 Create `app/dashboard/workspace/layout.tsx` — renders `WorkspaceSidebarNav` + `WorkspaceFilterContext.Provider` wrapping children slot
- [ ] 7.2 Create `app/dashboard/workspace/overview/page.tsx` — static imports for `MetricCard`/`PayoffRatio`; `next/dynamic` for `EquityCurveWidget` and `DrawdownWidget`; reads filter from `WorkspaceFilterContext`
- [ ] 7.3 Create `app/dashboard/workspace/calendar/page.tsx` — uses existing `Calendar` component and `useReportData` hook; no Recharts direct imports
- [ ] 7.4 Create `app/dashboard/workspace/reporting/page.tsx` — port from `app/dashboard/reporting/page.tsx`; all widgets already lazy-loaded; wire to `WorkspaceFilterContext` instead of local URL state
- [ ] 7.5 Create `app/dashboard/workspace/performance/strategy/page.tsx` — `next/dynamic` for `MaeMfeScatterWidget` and `DurationVsPnlScatterWidget`; reads filter from context
- [ ] 7.6 Create `app/dashboard/workspace/performance/behavior/page.tsx` — `next/dynamic` for `PsychologicalAttributionWidget` and `PlaybookPhaseHeatmapWidget`; reads filter from context

## 8. Legacy Route Redirects

- [ ] 8.1 Add redirect from `/dashboard/analytics` → `/dashboard/workspace/performance/strategy` (use Next.js `redirect()` in a minimal page or `next.config.js` redirects)
- [ ] 8.2 Add redirect from `/dashboard/reporting` → `/dashboard/workspace/reporting`
- [ ] 8.3 Update all internal `href` links in `app/dashboard/layout.tsx` sidebar nav that point to `/dashboard/analytics` or `/dashboard/reporting` to use workspace paths

## 9. Sidebar Nav Integration

- [ ] 9.1 Replace `AnalyticsNavSection` and `ReportingNavSection` inline code in `app/dashboard/layout.tsx` with the new `WorkspaceSidebarNav` component
- [ ] 9.2 Ensure `reporting_hub` feature flag check gates the REPORTING and PERFORMANCE sidebar sections in `WorkspaceSidebarNav`

## 10. Analytics Hub Lazy Loading (Existing Routes Fix)

- [ ] 10.1 Wrap `TimeAnalysisTab` Recharts components with `next/dynamic` in `app/dashboard/analytics/TimeAnalysisTab.tsx`
- [ ] 10.2 Wrap `StrategyAnalysisTab` Recharts components with `next/dynamic` in `app/dashboard/analytics/StrategyAnalysisTab.tsx`
- [ ] 10.3 Wrap `BehaviorAnalysisTab` Recharts components with `next/dynamic` in `app/dashboard/analytics/BehaviorAnalysisTab.tsx`
- [ ] 10.4 Wrap `RiskMetricsTab` Recharts components with `next/dynamic` in `app/dashboard/analytics/RiskMetricsTab.tsx`

## 12. Feature Flag Removal (Post-Rollout)

> Execute only after the workspace routes are confirmed stable in production.

- [ ] 12.1 Remove `"reporting_hub"` from `FeatureFlagKey` union type in `lib/featureFlags.ts`
- [ ] 12.2 Remove `reporting_hub` entry from `FEATURE_FLAGS` array in `lib/featureFlags.ts`
- [ ] 12.3 Remove `showReporting` variable and `features["reporting_hub"]` read in `app/dashboard/layout.tsx`
- [ ] 12.4 Remove all `reporting_hub` feature flag guards in `WorkspaceSidebarNav` — workspace routes are unconditionally visible
- [ ] 12.5 Remove `showReporting` parameter from `buildNavItems()` signature and all call sites
- [ ] 12.6 Delete `reporting_hub` feature flag record from the database (migration or manual cleanup)
- [ ] 12.7 Verify no TypeScript errors after removal (`tsc --noEmit`)

## 13. Test Coverage

### E2E Tests (Playwright)

- [ ] 13.1 Create `tests/specs/workspace-navigation.spec.ts` — verify all 5 workspace routes are reachable (`/overview`, `/calendar`, `/reporting`, `/performance/strategy`, `/performance/behavior`), sidebar is visible on each, and the correct sidebar item is active per route
- [ ] 13.2 Create `tests/specs/workspace-filter-state.spec.ts` — set date range on `/reporting`, navigate to `/performance/strategy`, verify URL search params are preserved and the same filter values are active; also verify filter bar debounce (rapid input produces single network request)
- [ ] 13.3 Update `tests/specs/reporting-hub.spec.ts` — change `beforeEach` URL from `/dashboard/reporting` to `/dashboard/workspace/reporting`; add a test that navigating to `/dashboard/reporting` redirects to `/dashboard/workspace/reporting`
- [ ] 13.4 Add test to `tests/specs/navigation.spec.ts` — verify `/dashboard/analytics` redirects to `/dashboard/workspace/performance/strategy`

### Unit Tests (Jest / React Testing Library)

- [ ] 13.5 Create `__tests__/components/workspace/WorkspaceFilterContext.test.tsx` — test: (a) initial state is read from URL params, (b) setter updates context value, (c) URL is not updated before 300ms debounce expires, (d) URL is updated after debounce
- [ ] 13.6 Create `__tests__/components/reporting/ScatterCircuitBreaker.test.tsx` — test `MaeMfeScatterWidget`: (a) renders `ScatterChart` when `data.length <= 500`, (b) renders fallback UI and NOT `ScatterChart` when `data.length > 500`; same for `DurationVsPnlScatterWidget`
- [ ] 13.7 Create `__tests__/components/reporting/AttributionUncategorized.test.tsx` — test `PsychologicalAttributionWidget`: (a) renders "Uncategorized" bar when input data contains entries with no check-in id, (b) "Uncategorized" bar is absent when all entries have a check-in id; same for `PlaybookPhaseHeatmapWidget`
- [ ] 13.8 Create `__tests__/components/reporting/MarketRegimeLabel.test.tsx` — snapshot or text assertion: `PsychologicalAttributionWidget` and `PlaybookPhaseHeatmapWidget` render the string "Market Regime" and do NOT render "Market Phase" anywhere in their output

## 11. Verification

- [ ] 11.1 Verify no Recharts imports exist as static top-level imports in any workspace route page file
- [ ] 11.2 Verify `staleTime` is set on all hooks used by workspace routes (grep for `useQuery` without `staleTime`)
- [ ] 11.3 Verify circuit breaker fallback renders correctly when mock scatter data exceeds 500 points (temporarily set `SCATTER_MAX_RAW_POINTS = 0` for testing)
- [ ] 11.4 Verify "Market Regime" label appears in behavior route attribution charts (no "Market Phase" visible in UI)
- [ ] 11.5 Verify "Uncategorized" group appears in attribution chart when test data has trades without check-in
- [ ] 11.6 Verify filter state persists when navigating Overview → Reporting → Strategy in the workspace
