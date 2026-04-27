## Context

The backend (Spec 1) introduces a mandatory `portfolio_id` on every data
endpoint. The current frontend has no awareness of portfolios: account filtering
is local `useState` on individual pages, the dashboard has no account scope at
all, and the sidebar houses the only sign-out control. This design establishes
the global state layer and the persistent top-bar that must exist before any
page can correctly call the new portfolio-scoped API.

Beyond portfolio context, the app requires a clear **multi-mode navigation
structure**. The three application modes are:

- **Portfolio Workspace** (Ebene A) — operational, portfolio-scoped. Sidebar:
  Dashboard, Journal, Reports, Quick Import. PortfolioSwitcher visible.
- **Global Library** (Ebene B) — strategic, portfolio-agnostic. Sidebar:
  Playbooks, Tags. PortfolioSwitcher hidden to signal global scope.
- **Market Check-in** (Ebene C) — chronological macro/psychological entries.
  Sidebar: Timeline. Deferred to a future spec; placeholder only in this spec.

Mode switching happens exclusively via a **BentoMenu** (nine-dot grid) in the
top-left of the TopBar.

**Current state at a glance:**
- State: one Zustand store (`authStore`) — token + user + hydrated flag only
- Layout: `app/dashboard/layout.tsx` (~800 lines) — sidebar-only shell; no
  desktop header
- Account scoping: ad-hoc `useState<string | null>` per page, passed to
  `AccountFilter` component
- Sign-out: sidebar bottom link only
- Mobile top bar: hamburger + logo, hidden on `lg+`
- Playbooks/Tags: standalone sidebar pages, no separation from operational data

---

## Goals / Non-Goals

**Goals:**

- Define a `appContextStore` Zustand slice for `activeContext` ('portfolio' |
  'library' | 'checkin'); persist to localStorage.
- Define a `portfolioStore` Zustand slice that is the single source of truth for
  `activePortfolioId` across the app; persist to localStorage.
- Implement `BentoMenu` — nine-dot button in top-left; popover listing the three
  contexts; switches `activeContext` and navigates to context root route.
- Implement `TopBar` — persistent desktop-and-mobile header; left: BentoMenu +
  wordmark; center: context-aware `PortfolioSwitcher`; right: `UserBadge`.
- Make `PortfolioSwitcher` visible only in Portfolio Workspace context.
- Make the sidebar render context-appropriate nav-items (same shell, different
  items per context).
- Handle the post-login cold-start case: if the user has no portfolios, show a
  gate that prompts creation instead of silently rendering a broken dashboard.
- Handle stale-ID recovery: if the persisted `activePortfolioId` no longer
  exists (portfolio deleted), fall back gracefully.
- Define the contract (`useActivePortfolio` hook) that all dashboard pages use
  to retrieve `activePortfolioId`.

**Non-Goals:**

- Creating or editing portfolios (Portfolio CRUD UI is Spec 3).
- Embedding `portfolioId` or `activeContext` in the URL path (see D1).
- Updating dashboard page internals to call new portfolio-scoped endpoints;
  this spec defines the contract; page-level migration is tracked in tasks.
- Backend changes — this spec is frontend-only.
- Full Market Check-in implementation (DailyCheckin entity, Timeline UI) —
  deferred to a future spec; BentoMenu entry and placeholder page only.
- Multi-portfolio comparison views.

---

## Decisions

### D1: Persistence via localStorage, NOT URL segment

**Chosen**: `activePortfolioId` is stored in `localStorage` under the key
`"active_portfolio_id"` and managed by the Zustand store. It is NOT part of the
URL path (e.g., not `/dashboard/portfolios/<id>/trades`).

**Alternatives considered:**

- *URL path segment* (`/dashboard/[portfolioId]/...`) — ensures deep-link
  sharability and browser-back behaviour. **Rejected** because:
  - All 20+ dashboard routes would need path-prefix refactoring.
  - Next.js App Router dynamic catch-all segments at the top level interact
    poorly with nested layouts.
  - Most users operate a single primary portfolio; deep-linking portfolio
    context is low value and high refactor cost.
  - Can be migrated to URL later without breaking the store abstraction if
    desired.

- *URL query param* (`?portfolio_id=<id>`) — less refactor than path segment.
  **Rejected** because query params leak into every `router.push`/`router.replace`
  call, pollute analytics URLs, and do not survive navigations that don't
  forward the param.

- *HTTP cookie* — could survive tab close; **rejected** because it requires
  server-side reads for SSR and adds complexity without clear benefit given
  the app is a fully client-rendered SPA shell.

**localStorage** is the right tradeoff here: zero routing changes, survives
refreshes, simple to implement, consistent with the existing `access_token`
pattern already in `authStore`.

---

### D2: New `portfolioStore.ts` file — not merged into `authStore`

**Chosen**: Create `stores/portfolioStore.ts` as a separate Zustand store.

**Alternatives considered:**

- *Add portfolio state directly to `authStore`* — simpler file count. **Rejected**
  because `authStore` models identity (who is logged in), while `portfolioStore`
  models workspace context (which portfolio is active). Mixing them violates
  single-responsibility and makes `authStore` harder to test.

**Rationale**: Two focused stores are easier to reason about and mock
independently in tests.

---

### D3: `useActivePortfolio` hook as the sole consumer API — no direct store imports in pages

**Chosen**: Dashboard pages and components MUST use `useActivePortfolio()` to
access the active portfolio. They MUST NOT import `usePortfolioStore` directly.

**Rationale**: The hook is the abstraction boundary. If persistence strategy
changes from localStorage to URL in a future spec, only the hook internals
change; no pages are touched. This follows the existing pattern where pages
use `useMetrics()` rather than calling TanStack Query directly.

**What the hook returns:**

```ts
interface UseActivePortfolioResult {
  activePortfolioId: string | null;
  activePortfolio: PortfolioRead | null;
  portfolios: PortfolioRead[];
  isLoading: boolean;
  setActivePortfolio: (id: string) => void;
}
```

Loading states: `isLoading = true` while the portfolio list is being fetched
OR while the store has not yet hydrated from localStorage. Pages should render
a skeleton/loading state when `isLoading` is true.

---

### D4: `EmptyPortfolioGate` rendered inside `dashboard/layout.tsx`

**Chosen**: After hydration, if `portfolios.length === 0`, the layout renders
`<EmptyPortfolioGate />` instead of `{children}`. The gate shows a single CTA
to create the first portfolio (links to `/dashboard/settings?tab=portfolios`
which is the portfolio CRUD UI from a future spec; for now it can link to a
modal or settings page stub).

**Alternatives considered:**

- *Redirect to a `/setup` route* — cleaner URL, but adds a new route and a
  redirect loop risk if the user navigates away. The in-layout gate keeps the
  URL at `/dashboard` which is simpler.
- *Show the dashboard with an empty state on each widget* — each widget would
  need its own empty state. **Rejected** as redundant; a single gate is clearer.

**Edge case — portfolio fetch failure:** If the `GET /portfolios` request fails
(network error / 500), the gate MUST NOT be shown. The layout shows an error
banner instead. Otherwise a transient API error would erroneously prompt the
user to "create a portfolio" they already have.

---

### D5: `TopBar` layout — BentoMenu left, context-aware center, UserBadge right

**Chosen**: The new `TopBar` is a full-width `<header>` rendered above both
sidebar and main content inside `app/dashboard/layout.tsx`. The existing
mobile hamburger+logo bar is removed (replaced).

**Layout structure after this change:**

```
┌─────────────────────────────────────────────────────────────┐
│  TopBar (h-14, full width, sticky)                           │
│  [⠿] Trade Sensei │ [PortfolioSwitcher*] │        [ JD ▼ ] │
│  * hidden in Library and Check-in contexts                   │
├──────────────┬──────────────────────────────────────────────┤
│  Sidebar     │  <main> page content                         │
│  (context-   │                                              │
│  specific    │                                              │
│  nav items)  │                                              │
└──────────────┴──────────────────────────────────────────────┘
```

**Sidebar nav-items by context:**

| Context | Nav items |
|---|---|
| `portfolio` | Dashboard, Journal, Reports, Quick Import |
| `library` | Playbooks, Tags |
| `checkin` | Timeline (placeholder) |

**Other sidebar changes:**
- Remove sign-out link from sidebar bottom (UserBadge dropdown handles it).
- Remove any standalone "Accounts" navigation links.
- Remove mobile hamburger top bar (TopBar handles this globally).
- Keep sidebar collapsible (Cmd/Ctrl+B) behaviour unchanged.

---

### D6: `BentoMenu` — nine-dot popover for context switching

**Chosen**: A `BentoMenu` button (nine-dot grid icon, `Grid3x3` or equivalent)
sits at the top-left of the TopBar, to the left of the wordmark. Clicking it
opens a Radix UI `Popover` listing the three application contexts.

**Popover entry layout per context:**
- Icon (distinct per context)
- Label: "Portfolio Workspace" / "Global Library" / "Market Check-in"
- Active indicator (e.g. filled dot or bold label) when `activeContext` matches
- Clicking a context entry: sets `appContextStore.setActiveContext(ctx)`, closes
  popover, navigates to context root route

**Context root routes:**

| Context | Root route |
|---|---|
| `portfolio` | `/dashboard` |
| `library` | `/dashboard/library` |
| `checkin` | `/dashboard/checkin` |

**Market Check-in entry**: visible in BentoMenu but navigates to a placeholder
page reading "Market Check-in — Coming Soon". No backend entity in this spec.

---

### D7: `appContextStore` — separate Zustand slice for application context

**Chosen**: Create `stores/appContextStore.ts` as a Zustand store separate from
both `authStore` and `portfolioStore`.

**Interface:**
```ts
type AppContext = 'portfolio' | 'library' | 'checkin'

interface AppContextState {
  activeContext: AppContext
  hydrated: boolean
  setActiveContext: (ctx: AppContext) => void
  hydrate: () => void
}
```

**Persistence**: `localStorage` key `"active_app_context"`. Default value when
key is absent: `'portfolio'`.

**Rationale**: `appContextStore` models top-level navigation mode; `portfolioStore`
models which portfolio is selected within portfolio mode. Mixing them would
couple two orthogonal concerns.

---

### D8: `PortfolioSwitcher` — context-aware visibility

**Chosen**: `PortfolioSwitcher` is rendered in the TopBar center slot only when
`activeContext === 'portfolio'`. In `library` and `checkin` contexts the center
slot is empty (or shows a context label if desired in a future iteration).

**Rationale**: The PortfolioSwitcher is meaningless and misleading in global
contexts — showing it suggests that Playbook or Check-in data is scoped to the
selected portfolio, which is incorrect.

**Implementation**: TopBar reads `activeContext` from `useAppContext()` (wraps
`appContextStore`) and conditionally renders `<PortfolioSwitcher />` or `null`.

**Dropdown content per portfolio row:**
- `color_hex` chip (12 px circle, `background-color: portfolio.color_hex`)
- Portfolio name
- Checkmark on the currently active entry

**Accessibility**: Keyboard-navigable (arrow keys, Enter, Escape) using Radix UI
`DropdownMenu`.

---

### D9: `UserBadge` — initials avatar, not a real avatar image

**Chosen**: Display a `<div>` with the user's initials (first char of `first_name`
+ first char of `last_name`, or first two chars of `email` as fallback).
Background colour is derived deterministically from the user's `id` (HSL hash).

**Dropdown items**: Settings (`/dashboard/settings`) and Sign Out (calls the
existing `useLogout()` mutation already used in the sidebar).

---

### D10: Stale `activePortfolioId` recovery

If the stored ID is not in the fetched portfolio list (deleted scenario):
1. Silently set `activePortfolioId` to the user's **default portfolio** if one
   is configured in `user_settings` (`default_portfolio_id` key); otherwise fall
   back to `portfolios[0].id` (sorted by `created_at asc`).
2. Persist the new ID to localStorage.
3. Do NOT show an error to the user.

If `portfolios` is empty, clear `activePortfolioId` to `null` and show the gate.

---

### D11: `usePortfolios` — wraps the regenerated OpenAPI client

**Chosen**: Create `hooks/usePortfolios.ts` that wraps the generated
`listPortfoliosApiV1PortfoliosGet` function. TanStack Query key `["portfolios"]`,
staleTime 60 s. Mirrors the existing pattern (e.g., `hooks/useAccounts.ts`).

**Note**: Hard dependency on Spec 1 being merged and `openapi-sync` having run.

---

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| Spec 1 not merged when work begins | `usePortfolios` has a mock fallback in local dev; store/hook can be stubbed first and wired later. |
| localStorage unavailable (SSR / incognito) | Both stores wrap `localStorage` access in `try/catch`; silently fall back to defaults. Next.js does not SSR dashboard pages. |
| Hydration flash — active context or portfolio ID not yet known | `isLoading: true` until both stores are `hydrated` and TanStack Query resolves; layout renders skeleton. |
| Portfolio fetch error shows empty gate falsely | D4 mitigation: only show gate when fetch _succeeds_ with empty array; show error banner on failure. |
| BentoMenu popover traps keyboard focus from TopBar | Use Radix `Popover` with `modal={false}` to keep sidebar accessible when popover is open. |
| Sidebar `useSettings()` still called without portfolio context | `useSettings()` is user-level, not portfolio-scoped — no change needed. |
| Playwright E2E tests break due to removed sidebar account links | Explicit test update step in tasks. |

---

## Migration Plan

No database changes. No backend changes. Frontend-only.

**Step 1 — Prerequisites (blocking)**
- Spec 1 merged
- `openapi-sync` run (TypeScript client regenerated with portfolio endpoints)

**Step 2 — State layer**
- `stores/appContextStore.ts` created
- `stores/portfolioStore.ts` created
- `hooks/useAppContext.ts` created
- `hooks/usePortfolios.ts` created
- `hooks/useActivePortfolio.ts` created

**Step 3 — Components**
- `components/layout/TopBar.tsx`
- `components/layout/BentoMenu.tsx`
- `components/layout/PortfolioSwitcher.tsx`
- `components/layout/UserBadge.tsx`
- `components/layout/EmptyPortfolioGate.tsx`

**Step 4 — Library context routes**
- `app/dashboard/library/page.tsx` (redirect to `/dashboard/library/playbooks`)
- `app/dashboard/library/playbooks/page.tsx`
- `app/dashboard/library/tags/page.tsx`
- `app/dashboard/checkin/page.tsx` (placeholder)
- Old `/dashboard/playbooks` and `/dashboard/tags` redirected to library routes

**Step 5 — Layout integration**
- `app/dashboard/layout.tsx` modified: integrate TopBar, context-aware sidebar
  nav, remove old mobile bar, remove sidebar account/sign-out links, add
  EmptyPortfolioGate

**Step 6 — Page migrations** (can run in parallel per page)
- Remove per-page `accountId` state and `AccountFilter` usage
- Read `activePortfolioId` via `useActivePortfolio`
- Pass `portfolioId` to relevant hooks

**Step 7 — Cleanup**
- Deprecate `AccountFilter` component if unused
- Update/add Playwright E2E tests

**Rollback**: Pure frontend change; reverting the commit set is sufficient.

---

## Open Questions

1. ~~Portfolio create flow~~ — **Resolved**: CTA links to
   `/dashboard/settings?tab=portfolios` (implemented in Spec 3).

2. ~~TopBar height and sidebar offset~~ — **Resolved**: CSS variable
   `--topbar-height: 3.5rem` used throughout; sidebar offset and main content
   padding both reference this variable (tasks 8.2, 8.11).

3. ~~PortfolioSwitcher on mobile~~ — **Resolved**: Always in TopBar on all
   screen sizes. The SidebarToggle handles sidebar visibility on mobile; no
   second PortfolioSwitcher implementation needed.

4. ~~Initials badge background colour~~ — **Resolved**: Deterministic HSL hash
   from `user.id` (string → sum of char codes → `hsl(N % 360, 65%, 48%)`).
   Keeps avatars stable across sessions and devices.
