## Context

The backend (Spec 1) introduces a mandatory `portfolio_id` on every data
endpoint. The current frontend has no awareness of portfolios: account filtering
is local `useState` on individual pages, the dashboard overview has no account
scope at all, and the sidebar houses the only sign-out control. This design
establishes the global state layer and the persistent top-bar that must exist
before any page can correctly call the new portfolio-scoped API.

**Current state at a glance:**
- State: one Zustand store (`authStore`) — token + user + hydrated flag only
- Layout: `app/dashboard/layout.tsx` (~800 lines) — sidebar-only shell; no
  desktop header
- Account scoping: ad-hoc `useState<string | null>` per page, passed to
  `AccountFilter` component
- Sign-out: sidebar bottom link only
- Mobile top bar: hamburger + logo, hidden on `lg+`

---

## Goals / Non-Goals

**Goals:**

- Define a `portfolioStore` Zustand slice that is the single source of truth for
  `activePortfolioId` across the app.
- Persist `activePortfolioId` to `localStorage` so it survives full page refreshes
  and Next.js navigation.
- Implement `TopBar` — a persistent desktop-and-mobile header above the page
  content; house the `PortfolioSwitcher` and `UserBadge` there.
- Handle the post-login cold-start case: if the user has no portfolios, show a
  gate that prompts creation instead of silently rendering a broken dashboard.
- Handle stale-ID recovery: if the persisted `activePortfolioId` no longer
  exists (portfolio deleted), fall back gracefully to the first available
  portfolio without crashing.
- Define the contract (`useActivePortfolio` hook) that all dashboard pages use
  to retrieve `activePortfolioId` — so no page imports from Zustand directly.

**Non-Goals:**

- Creating or editing portfolios (Portfolio CRUD UI is a separate spec).
- Embedding `portfolioId` in the URL path (see D1).
- Updating dashboard page internals to call new portfolio-scoped endpoints;
  this spec defines the contract; page-level migration is tracked in tasks but
  treated as mechanical find-replace work.
- Backend changes — this spec is frontend-only.
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

### D5: `TopBar` replaces both the existing mobile-only bar and sidebar brand area

**Chosen**: The new `TopBar` is a full-width `<header>` rendered above both
sidebar and main content inside `app/dashboard/layout.tsx`. The existing
mobile hamburger+logo bar is removed (replaced). The sidebar loses its top
brand area and relies on the `TopBar` for branding.

**Layout structure after this change:**

```
┌────────────────────────────────────────────────────────┐
│  TopBar (h-14, full width, sticky)                      │
│  Logo | PortfolioSwitcher (center) | UserBadge (right) │
├──────────────┬─────────────────────────────────────────┤
│  Sidebar     │  <main> page content                    │
│  (nav only)  │                                         │
└──────────────┴─────────────────────────────────────────┘
```

**Sidebar changes:**
- Remove sign-out link from sidebar bottom (UserBadge dropdown handles it).
- Remove any "Accounts" navigation links (Settings tab handles account management).
- Remove mobile hamburger top bar (TopBar handles this globally).
- Keep sidebar collapsible (Cmd/Ctrl+B) behaviour unchanged.

---

### D6: `PortfolioSwitcher` dropdown — render portfolio list via `usePortfolios` hook

**Chosen**: `PortfolioSwitcher` calls a `usePortfolios()` hook backed by TanStack
Query (key `["portfolios"]`, staleTime 60 s). Selecting a portfolio calls
`setActivePortfolio(id)` from `useActivePortfolio`.

**Dropdown content per portfolio row:**
- `color_hex` dot (12 px circle, `background-color: portfolio.color_hex`)
- Portfolio name
- `is_paper` badge: `PAPER` (amber) or `LIVE` (green)
- Checkmark on the currently active entry

**Accessibility**: The dropdown MUST be keyboard-navigable (arrow keys, Enter,
Escape) using Radix UI `DropdownMenu` (already used elsewhere in the codebase).

---

### D7: `UserBadge` — initials avatar, not a real avatar image

**Chosen**: Display a `<div>` with the user's initials (first char of `first_name`
+ first char of `last_name`, or first two chars of `email` as fallback).
Background colour is derived deterministically from the user's `id` (HSL hash).

**Rationale**: No avatar upload feature exists. A colour-coded initials badge is
consistent with the existing design language (Tags use `color_hex` chips).

**Dropdown items**: Settings (`/dashboard/settings`) and Sign Out (calls the
existing `useLogout()` mutation already used in the sidebar).

---

### D8: Stale `activePortfolioId` recovery

If the stored ID is not in the fetched portfolio list (deleted/renamed scenario):
1. Silently set `activePortfolioId` to `portfolios[0].id` (the first returned by
   the API — sorted by `created_at asc` on the backend).
2. Persist the new ID to localStorage.
3. Do NOT show an error to the user.

If `portfolios` is empty, clear `activePortfolioId` to `null` and show the gate.

---

### D9: `usePortfolios` — wraps the regenerated OpenAPI client

**Chosen**: Create `hooks/usePortfolios.ts` that wraps the generated
`listPortfoliosApiV1PortfoliosGet` function. This mirrors the existing pattern
(e.g., `hooks/useAccounts.ts`).

**Note**: This hook has a hard dependency on Spec 1 being merged and the
`openapi-sync` skill having been run. The tasks file marks this dependency
explicitly.

---

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| Spec 1 not merged when work begins | `usePortfolios` has a mock fallback in local dev; tasks are ordered so the store/hook can be stubbed first and wired later. |
| localStorage unavailable (SSR / incognito) | `portfolioStore.hydrate()` wraps `localStorage.getItem` in a `try/catch`; silently falls back to `null`. Next.js does not SSR dashboard pages (they are client-gated behind auth). |
| Hydration flash — active portfolio ID not yet known on first render | `isLoading: true` until both `portfolioStore.hydrated` and TanStack Query resolve; layout renders skeleton during this window. |
| Portfolio fetch error shows empty gate falsely | D4 mitigation: only show gate when fetch _succeeds_ and returns empty array; show error banner on failure. |
| Sidebar `useSettings()` still called without portfolio context | `useSettings()` calls a user-level settings endpoint (`/api/v1/users/me/settings`) which is not portfolio-scoped — no change needed. |
| Playwright E2E tests break due to removed sidebar account links | Tests that locate sidebar account-filter elements will fail; tasks include an explicit test update step. |

---

## Migration Plan

No database changes. No backend changes. Frontend-only.

**Step 1 — Prerequisites (blocking)**
- Spec 1 merged
- `openapi-sync` run (TypeScript client regenerated with portfolio endpoints)

**Step 2 — State layer**
- `stores/portfolioStore.ts` created
- `hooks/usePortfolios.ts` created
- `hooks/useActivePortfolio.ts` created

**Step 3 — Components**
- `components/layout/TopBar.tsx`
- `components/layout/PortfolioSwitcher.tsx`
- `components/layout/UserBadge.tsx`
- `components/layout/EmptyPortfolioGate.tsx`

**Step 4 — Layout integration**
- `app/dashboard/layout.tsx` modified: integrate TopBar, remove old mobile bar,
  remove sidebar account/sign-out links, add EmptyPortfolioGate

**Step 5 — Page migrations** (can run in parallel per page)
- Remove per-page `accountId` state and `AccountFilter` usage
- Read `activePortfolioId` via `useActivePortfolio`
- Pass `portfolioId` to relevant hooks

**Step 6 — Cleanup**
- Remove or deprecate `AccountFilter` component (if no longer used anywhere)
- Update/add Playwright E2E tests

**Rollback**: Pure frontend change; reverting the commit set is sufficient.
No data is mutated by this spec.

---

## Open Questions

1. **Portfolio create flow**: When `EmptyPortfolioGate` is shown, where does the
   CTA link? Spec 1 adds backend CRUD but the frontend Portfolio Settings UI is
   not yet implemented. Options: (a) link to a modal in the gate itself with a
   minimal create form, (b) link to a `/dashboard/settings?tab=portfolios` stub
   page that will be fleshed out in a later spec. Recommendation: (b) — keeps
   this spec focused.

2. **TopBar height and sidebar offset**: Current sidebar uses `top-0` with
   `h-screen`. Adding a 56 px (h-14) TopBar requires the sidebar to start at
   `top-14`. Should we use a CSS variable (`--topbar-height`) or hardcode?
   Recommendation: CSS variable — easier to adjust later.

3. **PortfolioSwitcher placement on mobile**: On `< lg` screens the sidebar is
   hidden. Should the `PortfolioSwitcher` remain in the TopBar (all sizes) or
   collapse into the sidebar on mobile? Recommendation: always in TopBar —
   simpler, avoids dual implementations.

4. **Colour of initials badge background**: Deterministic HSL from user ID keeps
   avatars stable across sessions. Should we instead use a fixed set of brand
   colours (e.g., the same set as portfolio colour options) for a more consistent
   look? This is a visual preference — no functional impact.
