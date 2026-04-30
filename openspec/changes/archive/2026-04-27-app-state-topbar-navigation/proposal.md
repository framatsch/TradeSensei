> **Execution order: Spec 2 of 3**
> Depends on: **Spec 1 (`portfolio-core-data-model`) must be merged and deployed.**
> Run `openapi-sync` after Spec 1 before starting this spec.
> See `openspec/changes/PORTFOLIO-EXECUTION-ORDER.md` for the full chain.

---

## Why

The backend is introducing a mandatory `portfolio_id` scope on every API
endpoint (Spec 1). The frontend currently has no global concept of an active
portfolio — account filtering is local per-page state and the dashboard has no
account scope at all. Without a global portfolio context every page would need
its own ad-hoc portfolio picker, creating inconsistency and making it impossible
to enforce the "one active portfolio drives the whole app" UX principle.

Beyond portfolio context, the app needs a clear separation between three distinct
application modes: the operational **Portfolio Workspace** (trading data scoped
to one portfolio), the strategic **Global Library** (portfolio-agnostic entities
like playbooks and tags), and the future **Market Check-in** (chronological
macro/psychological entries). A persistent `BentoMenu` (nine-dot grid) in the
top-left of the TopBar is the sole entry point for switching between these modes.

## What Changes

- **NEW** `appContextStore` Zustand slice — stores `activeContext:
  'portfolio' | 'library' | 'checkin'`; persisted to localStorage key
  `active_app_context`; distinct from `portfolioStore`.
- **NEW** `portfolioStore` Zustand slice — stores `activePortfolioId`,
  `activePortfolio` object, and a persist + hydrate mechanism (localStorage key
  `active_portfolio_id`).
- **NEW** `TopBar` component — desktop-always-visible header with:
  - Left: `BentoMenu` button (nine-dot grid icon) + app wordmark
  - Center: `PortfolioSwitcher` — visible **only** when `activeContext ===
    'portfolio'`; shows active portfolio name and `color_hex` dot; hidden in
    Library and Check-in contexts
  - Right: `UserBadge` — user initials avatar; opens dropdown with Settings and
    Logout links
- **NEW** `BentoMenu` component — popover/panel triggered by the nine-dot button;
  lists the three contexts with icon, label, and active indicator; selecting a
  context sets `activeContext` in `appContextStore` and navigates to the
  context's root route.
- **MODIFIED** `app/dashboard/layout.tsx` — integrate `TopBar` above the main
  content area; sidebar nav-items rendered conditionally by `activeContext`
  (Portfolio: Dashboard/Journal/Reports/Import; Library: Playbooks/Tags;
  Check-in: Timeline placeholder); remove the account-selection and sign-out
  links; remove the mobile-only top bar.
- **NEW** `EmptyPortfolioGate` component — shown when a user has no portfolios
  yet; prompts to create the first portfolio.
- **NEW** `useActivePortfolio` hook — reads `activePortfolioId` from the Zustand
  store, fetches portfolio list, resolves the active portfolio object, and
  handles edge-cases (no portfolios, stale ID, loading).
- **MODIFIED** All dashboard pages that call portfolio-scoped endpoints — pass
  `activePortfolioId` from the hook instead of the old per-page `accountId`
  state. (Each page migration is a separate task; this spec defines the contract
  the pages must follow.)
- **REMOVED** Per-page `AccountFilter` local state on Dashboard overview,
  Analytics, Calendar, and Reports pages (replaced by global context).
- **REMOVED** Sidebar account-selection UI (Account list / switcher links).
- **REMOVED** Sidebar Playbooks and Tags nav-links (moved to Library context).

## Capabilities

### New Capabilities

- `app-context-navigation`: Three-mode application structure (Portfolio Workspace /
  Global Library / Market Check-in) switchable via `BentoMenu`; active mode
  persisted in `appContextStore` (localStorage key `active_app_context`).
- `portfolio-context`: Global active-portfolio state stored in Zustand; persisted
  to localStorage; hydrated before first render; drives all portfolio-scoped API
  calls across the app.
- `topbar-navigation`: Persistent top-bar with `BentoMenu` (left), context-aware
  `PortfolioSwitcher` (center, portfolio mode only), and `UserBadge` (right);
  replaces the mobile-only bar and sidebar account links.
- `global-library-context`: Library mode renders the same sidebar shell with
  Playbooks and Tags nav-items; `PortfolioSwitcher` is hidden to make the
  global scope explicit; routes are under `/dashboard/library/*`.
- `market-checkin-placeholder`: Check-in mode is accessible via BentoMenu but
  renders a "Coming Soon" placeholder; the `DailyCheckin` entity and full UI
  are deferred to a future spec.
- `empty-portfolio-gate`: Intercept flow when a user has no portfolios — display
  a create-portfolio prompt instead of the main dashboard shell; handles the
  post-login cold-start edge case.

### Modified Capabilities

- `account-management`: The Settings page "Accounts" tab remains but is now
  scoped to `activePortfolioId`; the sidebar no longer exposes account management
  links.

## Impact

- **Frontend state**: New `appContextStore` Zustand slice (localStorage key
  `active_app_context`); new `portfolioStore` slice (localStorage key
  `active_portfolio_id`).
- **Frontend components**: New `TopBar`, `BentoMenu`, `PortfolioSwitcher`,
  `UserBadge`, `EmptyPortfolioGate` components; heavily modified
  `dashboard/layout.tsx` (context-aware sidebar nav).
- **Frontend hooks**: New `useActivePortfolio` hook; `usePortfolios` hook (wraps
  generated OpenAPI client); new `useAppContext` hook (wraps `appContextStore`).
- **Frontend routing**: New routes `/dashboard/library/playbooks` and
  `/dashboard/library/tags` for the Library context; existing
  `/dashboard/playbooks` and `/dashboard/tags` redirect to the new library
  routes. `activePortfolioId` is NOT embedded in the URL path (rationale in
  design.md). `activeContext` is NOT in the URL (persisted via localStorage
  only).
- **Backend / API**: No backend changes in this spec; Spec 1 API changes are a
  prerequisite. This spec assumes the generated OpenAPI client has been
  regenerated after Spec 1 is merged.
- **Testing**: Existing Playwright E2E tests that depend on the account-filter
  dropdown will need updating; new tests for portfolio switching, context
  switching via BentoMenu, and empty-state gate.
