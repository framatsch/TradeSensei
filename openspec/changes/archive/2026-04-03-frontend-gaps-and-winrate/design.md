## Context

The tradesensei backend exposes a comprehensive REST API (accounts CRUD, trade
CRUD with filtering/sorting/bulk ops, multiple timeseries endpoints, metrics
summary). The frontend currently uses only a subset of these endpoints:
dashboard overview, trade list (no filter/sort), trade detail (read-only), import,
playbooks, tags, and tax report.

There are two categories of missing work:
1. **Frontend gaps** — UI wiring to backend endpoints that already exist and are
   fully functional. These require no backend changes other than one bug fix.
2. **Winrate development** — one new backend endpoint (`/timeseries/rolling-winrate`)
   plus two chart components.

The codebase uses Next.js 14 App Router, TanStack Query for data fetching, Zustand
for auth state, Recharts for charts, and an openapi-ts generated client. Backend is
FastAPI with SQLAlchemy async, Pydantic v2.

## Goals / Non-Goals

**Goals:**
- Expose all existing backend capabilities in the frontend
- Fix the `TradeUpdate` sentinel bug so `stop_loss`/`take_profit` can be cleared to null
- Resolve playbook name in `TradeRead` to avoid an extra frontend round-trip
- Add rolling winrate endpoint and chart
- Keep changes additive — no regressions to existing pages

**Non-Goals:**
- Psychology analysis, risk analysis, checklists, trading plans, simulator — out of scope for this change
- Mobile layout optimisation
- Any new backend data models or DB migrations (except the `TradeRead` field addition and the new timeseries endpoint)
- Authentication or authorisation changes

## Decisions

### D1: Playbook name resolution — backend vs. frontend join

**Decision:** Add `playbook_name: str | None` as a computed field on `TradeRead`,
populated by a joined load in the trades repository.

**Rationale:** The trade detail page currently shows a raw UUID. A second API call
to resolve it adds latency and complexity. The trades repository already eager-loads
tags via `selectin` loading — adding the playbook relationship join is a small
consistent change. The OpenAPI client regeneration will surface the new field
automatically.

**Alternative considered:** Resolve in frontend using `usePlaybooks()` — rejected
because it creates a dependency between two unrelated queries and shows a flash of
UUID before the playbook list loads.

---

### D2: TradeUpdate sentinel pattern for nullable stop_loss / take_profit

**Decision:** Introduce a `UNSET` sentinel using `pydantic.fields.PydanticUndefinedType`
or a typed `NotGiven` wrapper so the service layer can distinguish "field not
provided" from "field explicitly set to null".

**Rationale:** The current `TradeUpdate` schema uses `None` for both "not provided"
and "clear the value". The service layer cannot tell them apart. A sentinel approach
(the same pattern used by the OpenAI SDK and many Pydantic v2 codebases) is the
idiomatic fix.

**Alternative considered:** Separate `PATCH /trades/{id}/clear-stop-loss` endpoint
— rejected as over-engineering for a straightforward null-clear scenario.

---

### D3: Filter state persistence — URL query params

**Decision:** Trade list filters are stored in URL search params via Next.js
`useSearchParams` + `router.replace`.

**Rationale:** URL-persisted filters are shareable, survive page refresh, and
work with the browser back button. They require no additional client state store.

**Alternative considered:** Zustand store for filter state — rejected because it
doesn't survive reload and breaks browser navigation.

---

### D4: Bulk selection state — local component state

**Decision:** The set of selected trade IDs is stored in `useState` within the
`TradeTable` component, not in a global store.

**Rationale:** Selection is ephemeral UI state scoped to the trade list page.
There is no need for cross-page access. Local state is simpler and avoids
polluting the global Zustand store.

---

### D5: Trade create/edit — shared form component, route-based

**Decision:** A single `TradeForm` component handles both create and edit modes.
Create is accessed via a button linking to `/dashboard/trades/new`. Edit is
accessed via an "Edit" button on the trade detail page that navigates to
`/dashboard/trades/[id]/edit`.

**Rationale:** A dedicated route (not a modal) keeps the URL meaningful,
supports deep-linking, and avoids z-index/scroll issues with modals containing
date pickers. The shared component reduces duplication.

**Alternative considered:** Modal dialog for both — rejected due to complexity
with nested form elements and date/time inputs.

---

### D6: Rolling winrate backend — Python sliding window, no raw SQL

**Decision:** The rolling winrate endpoint fetches all closed trades for the
user (already ordered by `closed_at`), then computes the sliding window in
Python using a `deque`.

**Rationale:** Consistent with how `get_monthly_pnl()` works (also computes in
Python after fetching the raw series). Avoids complex window-function SQL that
would be harder to test. Trade counts per user are not expected to exceed tens
of thousands, so Python iteration is acceptable.

**Alternative considered:** PostgreSQL `AVG() OVER (ROWS N PRECEDING)` window
function — rejected for now due to added query complexity and testing overhead.

---

### D7: Dashboard analytics layout

**Decision:** Add the three new charts (Monthly PnL, Return Distribution, PnL
by Asset Class) in a new "Analytics" section below the existing daily PnL chart.
Add the winrate charts in a "Win Rate Development" section below that.

**Rationale:** Additive — no existing layout is disturbed. Each section is a
clearly labelled `<section>` block with a heading, matching the existing style.

## Risks / Trade-offs

- **Large trade datasets in simulator hooks:** `useRollingWinrate` fetches all
  closed trades. For users with thousands of trades this could be slow.
  → Mitigation: apply the same `from_dt`/`to_dt` filter params available on
  other timeseries endpoints; add a default limit of 2000 points in the response.

- **OpenAPI client drift:** Adding `playbook_name` to `TradeRead` and the new
  rolling-winrate endpoint requires regenerating the frontend client. If the
  client is not regenerated, TypeScript will not know about the new field.
  → Mitigation: regenerate client as part of the task sequence before frontend
  work starts.

- **Sentinel pattern complexity:** The `UNSET` sentinel adds Pydantic v2 model
  complexity. Incorrect usage in tests could mask bugs.
  → Mitigation: cover the null-clear path with a dedicated integration test.
