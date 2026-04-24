## Why

The backend is introducing a mandatory `portfolio_id` scope on every API
endpoint (Spec 1). The frontend currently has no global concept of an active
portfolio — account filtering is local per-page state and the dashboard has no
account scope at all. Without a global portfolio context every page would need
its own ad-hoc portfolio picker, creating inconsistency and making it impossible
to enforce the "one active portfolio drives the whole app" UX principle.

## What Changes

- **NEW** `portfolioStore` Zustand slice — stores `activePortfolioId`,
  `activePortfolio` object, and a persist + hydrate mechanism (localStorage key
  `active_portfolio_id`).
- **NEW** `TopBar` component — desktop-always-visible header with:
  - Left: app logo / brand wordmark
  - Center: `PortfolioSwitcher` — shows active portfolio name, `color_hex`
    indicator dot, and `is_paper` badge; opens a dropdown to switch portfolios
  - Right: `UserBadge` — user initials avatar; opens dropdown with Settings and
    Logout links
- **MODIFIED** `app/dashboard/layout.tsx` — integrate `TopBar` above the main
  content area; remove the account-selection and sign-out links from the sidebar;
  remove the mobile-only top bar (replaced by `TopBar`).
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

## Capabilities

### New Capabilities

- `portfolio-context`: Global active-portfolio state stored in Zustand; persisted
  to localStorage; hydrated before first render; drives all portfolio-scoped API
  calls across the app.
- `topbar-navigation`: Persistent top-bar component that renders the portfolio
  switcher (name, color, paper/live badge) and the user badge with settings /
  logout dropdown; replaces the mobile-only bar and sidebar account links.
- `empty-portfolio-gate`: Intercept flow when a user has no portfolios — display
  a create-portfolio prompt instead of the main dashboard shell; handles the
  post-login cold-start edge case.

### Modified Capabilities

- `account-management`: The Settings page "Accounts" tab remains but is now
  scoped to `activePortfolioId`; the sidebar no longer exposes account management
  links.

## Impact

- **Frontend state**: New Zustand store slice; localStorage key
  `active_portfolio_id`.
- **Frontend components**: New `TopBar`, `PortfolioSwitcher`, `UserBadge`,
  `EmptyPortfolioGate` components; heavily modified `dashboard/layout.tsx`.
- **Frontend hooks**: New `useActivePortfolio` hook; `usePortfolios` hook (wraps
  generated OpenAPI client).
- **Frontend routing**: No new routes; URL structure unchanged. `activePortfolioId`
  is NOT embedded in the URL path (rationale in design.md).
- **Backend / API**: No backend changes in this spec; Spec 1 API changes are a
  prerequisite. This spec assumes the generated OpenAPI client has been
  regenerated after Spec 1 is merged.
- **Testing**: Existing Playwright E2E tests that depend on the account-filter
  dropdown will need updating; new tests for portfolio switching and empty-state
  gate.
