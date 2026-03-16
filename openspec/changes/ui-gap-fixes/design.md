## Context

The backend API surface is fully implemented (Iterations 1–6). All required endpoints for account management, trade CRUD with nullable fields, bulk operations, Flex Query import, and time-series analytics exist and are stable. The frontend TypeScript OpenAPI client (`frontend/src/client/`) is already generated from this spec. The gap is entirely in the frontend presentation layer: missing pages, missing form wiring, and one minor backend schema bug (nullable sentinel on `TradeUpdate`).

## Goals / Non-Goals

**Goals:**
- Give users access to all backend capabilities from the UI
- Fix the `TradeUpdate` nullable sentinel so `stop_loss` / `take_profit` can be explicitly cleared
- Keep all changes additive — no existing pages or components are removed or broken
- Maintain strict TypeScript, Tailwind-only styling, and React Query for all data fetching
- Wire every new data-fetching operation through the existing generated API client

**Non-Goals:**
- Adding new backend endpoints (all required endpoints already exist)
- Redesigning existing pages that already work (trade list layout, dashboard card grid, auth pages)
- Adding real-time / WebSocket updates
- Mobile-responsive redesign (responsive improvements may be incidental)

## Decisions

### D1: Trade edit form — inline vs. separate page
Chosen: **Inline editing on the existing `/dashboard/trades/[id]` page via an "Edit" toggle.**
- Keeps the user on the same page; no navigation round-trip
- Avoids duplicating the trade detail route
- Alternative (separate `/dashboard/trades/[id]/edit` route) was rejected: doubles URL surface, complicates breadcrumbs, no benefit for a single-record form

### D2: Filter state persistence — URL query params vs. local state
Chosen: **URL query params via Next.js `useSearchParams` / `useRouter`.**
- Filters survive page refresh and are shareable/bookmarkable
- React Query cache key already derives from the filter object, so URL params integrate cleanly
- Alternative (Zustand store) was rejected: filter state is not truly global; URL params are the standard Next.js App Router pattern

### D3: Bulk selection state — local component state vs. Zustand
Chosen: **Local `useState` in `TradeTable`** (set of selected trade IDs).
- Selection is ephemeral and page-scoped; no other component needs it
- Avoids polluting the global store with transient UI state

### D4: `TradeUpdate` nullable sentinel — `null` literal vs. explicit `UNSET` sentinel
Chosen: **`Optional[T]` with `model_validator` that treats an explicit `null` JSON value as "clear the field".**
- Pydantic v2 distinguishes `field not present` (UNSET) from `field = null` via `model_fields_set`
- Frontend sends `null` to clear; omits the field to leave it unchanged
- Alternative (a dedicated `CLEAR` string sentinel) was rejected: non-standard, confusing for API consumers

### D5: Extended analytics placement
Chosen: **Second row on the existing `/dashboard` page** (below the equity/drawdown charts), not a new `/dashboard/analytics` page.
- Avoids adding navigation entries for charts that are natural companions to the existing dashboard
- `PnlBySymbolChart` already exists as a component and just needs placement

### D6: Account management page
Chosen: **`/dashboard/accounts` as a new sidebar-linked page**, mirroring the Playbooks and Tags pages pattern.
- Consistent UX pattern already established by those pages
- Accounts are a first-class resource that deserves its own page

## Risks / Trade-offs

- [Inline trade edit form is large] → Break into logical sections (Entry, Exit, Tags & Playbook, Notes) with a tabbed or sectioned layout to avoid an overwhelming single form.
- [Filter bar adds visual complexity to the trade list] → Collapse filters behind a "Filters" toggle button; show active filter count badge.
- [Bulk operations are destructive] → Require a confirmation dialog for bulk delete; bulk assign is reversible so no confirmation needed.
- [Flex Query calls the live IBKR API from the backend] → The existing `flex_import_service` handles timeout/error propagation; the UI just needs to surface those errors clearly.
- [Nullable sentinel backend fix touches the trade update path] → Covered by existing integration tests; add a targeted unit test for the `null`-clear behavior.
