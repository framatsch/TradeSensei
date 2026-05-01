## Context

The dashboard currently uses a single `DashboardLayout` with a global sidebar that switches content based on `activeContext` (portfolio, library, checkin). The Trading Log (`/dashboard/trades`) is a standard full-page table with a global sidebar navigation. The actions (New Trade, Quick Import, CSV Export) and saved filter links live in the same sidebar as all other navigation items, creating cognitive fragmentation between operational and analytical workflows.

The prompt requires:
1. **Pillar Architecture** — three visually isolated workspaces: Portfolio Workspace, Trading Log, Market Check-in.
2. **Trading Log Operative Sidebar** — a dedicated left sidebar with an Actions section and a Saved Filters section.
3. **Collapsible Filter Configurator** — inline collapsible filter bar above the table with a Save Filter button.
4. **URL-synced filter state** — all active filter parameters reflected in URL search params.
5. **Reporting Hub dynamic sub-links** — `SavedDashboardView` entries appended under "Reporting Hub" in the Portfolio Workspace sidebar.

The existing codebase already has:
- `useSavedTradeFilters()` hook and `SavedTradeFilterRead` types.
- `TradesPageClient` with filtering logic (`useTradeFilterParams` is currently inline in the trades page).
- `reporting-hub-analytics-ui` change already implemented at `/dashboard/reporting`.
- `AppContext` store with `portfolio | library | checkin` enum — pillar routing maps to contexts.

## Goals / Non-Goals

**Goals:**
- Introduce a dedicated `TradingLogLayout` (`/dashboard/trades/layout.tsx`) with its own left sidebar (Actions + Saved Filters), replacing the global sidebar for all `/dashboard/trades` routes.
- Introduce a `WorkspaceLayout` (`/dashboard/workspace/layout.tsx`) or extend Portfolio context sidebar with `SavedDashboardView` sub-links under Reporting Hub.
- Extract filter-to-URL logic into a reusable `useTradeFilterParams` hook.
- Add a collapsible `FilterConfigurator` component at the top of the trade table.
- Ensure `TradingLog` components do not import Recharts or other heavy charting libraries.

**Non-Goals:**
- Restructuring routing to move existing pages (`/dashboard/reporting`, `/dashboard/checkin`) — they keep their current paths; the "pillar" is a layout and nav model, not a URL migration.
- Implementing a full workspace switcher beyond the existing Bento Menu (`TopBar`).
- Adding new backend endpoints (all data already exists).
- Responsive/mobile redesign of the new sidebar.

## Decisions

### Decision 1: Trading Log gets its own nested layout instead of a global sidebar switch

**Chosen:** Add `app/dashboard/trades/layout.tsx` with a dedicated sidebar.

**Alternative:** Add a conditional render inside `DashboardLayout` for `pathname.startsWith("/dashboard/trades")`.

**Rationale:** A nested layout keeps the Trading Log sidebar self-contained, avoids `DashboardLayout` becoming a large conditional tree, and is idiomatic Next.js App Router. The existing layout still wraps trades (TopBar, auth guard, portfolio gate), while the trades layout adds its own inner sidebar. The trades layout will render children inside a two-column flex row.

### Decision 2: Hide global sidebar on trades routes

The global sidebar in `DashboardLayout` should not be shown when on `/dashboard/trades` routes — the operative sidebar in `TradingLogLayout` replaces it. Rather than a complex conditional, we pass a `hideOnPaths` prop or check `pathname` inside `DashboardLayout` to suppress the sidebar for trades routes.

**Chosen:** Add a simple `isTradesRoute` check in `DashboardLayout` that omits the `<aside>` when `pathname.startsWith("/dashboard/trades")`. The main content div expands to full width.

### Decision 3: Filter Configurator is a collapsible panel, not a modal

The filter bar lives above the table inline, collapsed by default on mobile, expanded by default on desktop. State (open/closed) is local to the `FilterConfigurator` component — not synced to URL.

### Decision 4: URL sync via `useTradeFilterParams` hook

Extract the existing filter-to-URL logic from `TradesPageClient` into a dedicated hook at `hooks/useTradeFilterParams.ts`. This hook encapsulates `useSearchParams`, `useRouter`, and provides `filters`, `setFilter`, `clearFilters`, and `savedViewId` helpers.

### Decision 5: SavedDashboardView sub-links in Portfolio sidebar

The `reporting-hub-ui` change already fetches saved views. We add a `useReportingViews()` hook (or reuse the existing query) in the dashboard layout to append sub-links under "Reporting Hub" when `activeContext === 'portfolio'`. Links navigate to `/dashboard/reporting?view_id=<id>`.

## Risks / Trade-offs

- [Nested layout adds extra DOM wrapper] → Mitigation: Ensure inner layout uses `flex-1 min-w-0` to fill available space; verify no double scrollbars by auditing overflow classes.
- [TradingLogLayout must not break /dashboard/trades/[id] and /dashboard/trades/new routes] → Mitigation: The layout wraps all children; detail/new pages do not use the operative sidebar, so we conditionally render it only for the index route OR accept the sidebar appearing on sub-routes (consistent with the design's "pillar isolation" principle).
- [Filter state duplication between hook and sidebar] → Mitigation: The `useTradeFilterParams` hook is the single source of truth; both `FilterConfigurator` and `TradingLogSidebar` call the same hook.
- [Heavy chart library import into TradingLog] → Mitigation: Audit `TradesPageClient` imports; recharts must not appear in the trades component tree. If found, extract offending components.

## Open Questions

- Should the operative sidebar also appear on the Trade Detail page (`/dashboard/trades/[id]`), or only on the trades index? The mockup only shows the index. For now: show sidebar on all `/dashboard/trades` routes for architectural consistency but leave this open for UX review.
- Should `SavedDashboardView` sub-links use the existing `useSavedDashboardViews` query (if it exists) or a new one? Check API client for existing hooks before adding new.
