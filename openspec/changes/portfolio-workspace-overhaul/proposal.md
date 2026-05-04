## Why

The Portfolio Workspace currently suffers from two critical issues: a monolithic single-page dashboard (`/dashboard/reporting/page.tsx`) that synchronously mounts all Recharts widgets causing main-thread blocking and browser freezes, and a fragmented route structure where Analytics Hub (`/dashboard/analytics`) and Reporting Hub (`/dashboard/reporting`) are disconnected rather than unified under a coherent workspace. The existing `pillar-routing` and `reporting-hub-ui` specs define the right architecture, but the implementation has not been consolidated into isolated, performant routes under `/dashboard/workspace/`.

## What Changes

- **NEW** multi-route workspace under `/dashboard/workspace/` consolidating current `/dashboard/analytics` and `/dashboard/reporting` into 5 isolated routes: `/overview`, `/calendar`, `/reporting`, `/performance/strategy`, `/performance/behavior`
- **REFACTOR** `app/dashboard/layout.tsx` sidebar nav — unify the current split `AnalyticsNavSection` + `ReportingNavSection` into a single `WorkspaceSidebarNav` matching the spec mockup (Analytics + Reporting + Performance sections)
- **REFACTOR** `app/dashboard/analytics/` tab-based page → split into isolated route files with `next/dynamic` lazy loading for each Recharts component
- **REFACTOR** `hooks/useReportingAnalytics.ts` — add `staleTime: 5 * 60 * 1000` and stable `filter_config`-derived query keys to all hooks; replace mock `useScatterAnalytics` with real API when available, otherwise wire circuit breaker on > 500 point threshold
- **REFACTOR** `ReportFilterBar` — add 300ms debounce on all text/select inputs; implement `AbortController`-based request cancellation
- **RENAME** all `MarketPhase` → `MarketRegime` across frontend (UI labels, component display text, not API field names which stay as-is until backend changes)
- **FIX** `PsychologicalAttributionWidget` and `PlaybookPhaseHeatmapWidget` to render "Uncategorized" for trades without a linked daily check-in, not silently omit them
- **REDIRECT** `/dashboard/analytics` and `/dashboard/reporting` to their new workspace equivalents (or keep as aliases)
- **REMOVE** `/dashboard/reports/` sub-routes (consolidate into workspace)

## Capabilities

### New Capabilities

- `workspace-route-isolation`: Multi-route architecture under `/dashboard/workspace/` with 5 isolated page routes, persistent sidebar, and URL-synced global filter state shared across all sub-routes via context
- `anti-lag-performance`: `next/dynamic` lazy loading for all Recharts widgets in analytics hub tabs, `staleTime`-based TanStack Query caching, scatter circuit breaker (> 500 points → fallback UI), 300ms debounced filter bar with request cancellation

### Modified Capabilities

- `reporting-hub-ui`: Sidebar nav restructure to match unified workspace sidebar mockup; saved views sub-links remain but now under the new nav section
- `pillar-routing`: `/dashboard/workspace/` is the canonical Portfolio Workspace base path; legacy paths redirect

## Impact

- **Files modified:** `app/dashboard/layout.tsx`, `app/dashboard/reporting/page.tsx`, `app/dashboard/analytics/page.tsx` and all tab files, `hooks/useReportingAnalytics.ts`, `components/reporting/Widgets.tsx`, `components/reporting/ReportFilterBar.tsx`
- **Files created:** `app/dashboard/workspace/layout.tsx`, `app/dashboard/workspace/overview/page.tsx`, `app/dashboard/workspace/calendar/page.tsx`, `app/dashboard/workspace/reporting/page.tsx`, `app/dashboard/workspace/performance/strategy/page.tsx`, `app/dashboard/workspace/performance/behavior/page.tsx`, `components/workspace/WorkspaceSidebarNav.tsx`, `components/workspace/WorkspaceFilterContext.tsx`
- **No backend changes required** — existing API endpoints are sufficient; scatter endpoint uses circuit breaker on raw data
- **Feature flag:** `reporting_hub` flag gates apply to the new workspace routes identically
