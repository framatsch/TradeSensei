## 0. Prerequisites (blocking — verify before starting)

- [ ] 0.1 Confirm Spec 1 (`portfolio-core-data-model`) backend changes are merged and deployed to the dev environment
- [ ] 0.2 Run `openapi-sync` skill to regenerate the TypeScript client after Spec 1; verify `listPortfoliosApiV1PortfoliosGet` and related functions appear in `frontend/lib/api/`
- [ ] 0.3 Verify Zustand v5 is available (`"zustand": "^5.0.11"` in `frontend/package.json`) — no install needed

## 1. Portfolio Zustand Store

- [ ] 1.1 Create `frontend/stores/portfolioStore.ts` — define `PortfolioState` interface with `activePortfolioId: string | null`, `hydrated: boolean`, `setActivePortfolioId(id: string): void`, `clearActivePortfolioId(): void`, `hydrate(): void`
- [ ] 1.2 Implement `hydrate()` in the store: wrap `localStorage.getItem("active_portfolio_id")` in `try/catch`; on success set `activePortfolioId` to stored value or `null`; always set `hydrated = true`
- [ ] 1.3 Implement `setActivePortfolioId()`: update store state AND call `localStorage.setItem("active_portfolio_id", id)` wrapped in `try/catch`
- [ ] 1.4 Implement `clearActivePortfolioId()`: set `activePortfolioId = null` and call `localStorage.removeItem("active_portfolio_id")` wrapped in `try/catch`
- [ ] 1.5 Export `usePortfolioStore` hook from `frontend/stores/portfolioStore.ts`

## 2. Portfolio Hooks

- [ ] 2.1 Create `frontend/hooks/usePortfolios.ts` — wrap `listPortfoliosApiV1PortfoliosGet` (generated OpenAPI client) with TanStack Query key `["portfolios"]`, staleTime 60 000 ms; return `{ portfolios: PortfolioRead[], isLoading, isError }`
- [ ] 2.2 Create `frontend/hooks/useActivePortfolio.ts` — implement `useActivePortfolio()` hook:
  - Read `activePortfolioId` and `hydrated` from `usePortfolioStore`
  - Call `usePortfolios()` for the list
  - Resolve active portfolio object (cross-reference by id)
  - Handle stale ID: if stored ID not in list AND list non-empty → call `setActivePortfolioId(portfolios[0].id)`
  - Handle empty list: call `clearActivePortfolioId()`
  - Set `isLoading = !hydrated || portfoliosQuery.isLoading`
  - Return `{ activePortfolioId, activePortfolio, portfolios, isLoading, setActivePortfolio }`
- [ ] 2.3 Call `portfolioStore.hydrate()` in `frontend/app/providers.tsx` (inside `useEffect` on mount, client-side only) so it runs before any dashboard page renders

## 3. TopBar Component

- [ ] 3.1 Create `frontend/components/layout/TopBar.tsx` — full-width `<header>` (`h-14`, sticky, `border-b bg-background z-40`); left: logo/wordmark; center: `<PortfolioSwitcher />`; right: `<UserBadge />`
- [ ] 3.2 Create `frontend/components/layout/PortfolioSwitcher.tsx` — trigger button showing colour dot + portfolio name + LIVE/PAPER badge; on click opens Radix UI `DropdownMenu`; each menu item shows colour dot, name, badge, and checkmark if active; calls `setActivePortfolio(id)` on item select; renders skeleton when `isLoading`
- [ ] 3.3 Create `frontend/components/layout/UserBadge.tsx` — renders initials avatar (first char `first_name` + first char `last_name`; fallback first 2 chars of email; both uppercased); background colour derived from user `id` via HSL hash; on click opens Radix UI `DropdownMenu` with "Settings" link and "Sign Out" button; "Sign Out" calls existing `useLogout()` mutation

## 4. EmptyPortfolioGate Component

- [ ] 4.1 Create `frontend/components/layout/EmptyPortfolioGate.tsx` — renders a centred card with an icon, heading ("No portfolios yet"), description, and primary CTA button "Create your first portfolio" that navigates to `/dashboard/settings?tab=portfolios`; TopBar is still rendered above this gate

## 5. Dashboard Layout Integration

- [ ] 5.1 Read `frontend/app/dashboard/layout.tsx` in full before editing
- [ ] 5.2 Add CSS variable `--topbar-height: 3.5rem` (56 px) to the layout root element; update sidebar top offset from `top-0` to `top-[var(--topbar-height)]` and height from `h-screen` to `h-[calc(100vh-var(--topbar-height))]`
- [ ] 5.3 Insert `<TopBar />` as the first child of the layout's outermost `<div>`, above the sidebar and `<main>` wrapper
- [ ] 5.4 Remove the existing mobile-only hamburger + logo top bar (the `<div className="... lg:hidden ...">` block) — `TopBar` replaces it on all screen sizes
- [ ] 5.5 Remove the "Sign Out" nav item from the sidebar bottom section — it now lives in `UserBadge`
- [ ] 5.6 Remove any "Accounts" standalone sidebar nav link (account management remains accessible via Settings)
- [ ] 5.7 Add `EmptyPortfolioGate` conditional: after auth check, call `useActivePortfolio()`; if `!isLoading && portfolios.length === 0` render `<EmptyPortfolioGate />`; if `isLoading` render skeleton; if `portfolios.length > 0` render `{children}` as normal
- [ ] 5.8 Add portfolio fetch error handling: if `usePortfolios()` returns `isError === true` render an error banner (`"Failed to load portfolios — please refresh"`) instead of `EmptyPortfolioGate`
- [ ] 5.9 Update main content area `<main>` top padding/margin to account for TopBar height using `pt-14` or the CSS variable

## 6. Page Migrations — Remove Per-Page AccountFilter State

- [ ] 6.1 `frontend/app/dashboard/page.tsx` (Overview) — remove any `accountId` state; pass `activePortfolioId` from `useActivePortfolio()` to `useMetrics()`; update `useMetrics` hook signature to accept `portfolioId`
- [ ] 6.2 `frontend/app/dashboard/analytics/page.tsx` — remove `accountId` state and `<AccountFilter>`; read `activePortfolioId` and pass to `useReportData()`
- [ ] 6.3 `frontend/app/dashboard/reports/calendar/page.tsx` — remove `accountId` state and `<AccountFilter>`; pass `activePortfolioId` to the calendar data hook
- [ ] 6.4 `frontend/app/dashboard/cash/CashPageClient.tsx` — remove `accountId` state and `<AccountFilter>`; pass `activePortfolioId` to cash data hooks
- [ ] 6.5 `frontend/app/dashboard/trades/page.tsx` — remove `account_id` query-param logic; ensure trades list hook accepts `portfolioId` from `useActivePortfolio()`
- [ ] 6.6 Review all other dashboard pages for any remaining `AccountFilter` usage via `rg "AccountFilter" frontend/` and migrate

## 7. Hook Updates — Accept portfolioId

- [ ] 7.1 Update `frontend/hooks/useMetrics.ts` to accept `portfolioId: string` and include it in the API call path/params (per new portfolio-scoped endpoint from Spec 1)
- [ ] 7.2 Update `frontend/hooks/useEquityCurve.ts` and `useDrawdown.ts` similarly
- [ ] 7.3 Update `frontend/hooks/useAccounts.ts` to accept optional `portfolioId` and scope the `GET /portfolios/{portfolioId}/accounts` call
- [ ] 7.4 Update `frontend/hooks/useTrades.ts` (or equivalent) to accept `portfolioId` and call the portfolio-scoped endpoint

## 8. Cleanup

- [ ] 8.1 Check if `frontend/components/ui/AccountFilter.tsx` is still used anywhere after step 6.6; if unused, mark it deprecated with a JSDoc comment `/** @deprecated — replaced by global portfolio context */` (do NOT delete yet to avoid breaking any remaining references)
- [ ] 8.2 Run `npm run build` in `frontend/` and fix all TypeScript errors

## 9. Tests

- [ ] 9.1 Write unit test for `portfolioStore`: hydration from localStorage, stale-ID fallback, localStorage unavailable (mock `localStorage.getItem` to throw)
- [ ] 9.2 Write unit test for `useActivePortfolio`: covers empty list → gate, stale ID → fallback, loading states
- [ ] 9.3 Update any Playwright E2E tests that previously located a sidebar "Sign Out" button — change selector to the UserBadge dropdown
- [ ] 9.4 Update any Playwright E2E tests that previously used `<AccountFilter>` / account dropdown — these should now rely on the global portfolio context
- [ ] 9.5 Add Playwright E2E test: `empty-portfolio-gate.spec.ts` — mock `GET /portfolios` to return empty array; verify gate is shown and CTA navigates correctly

## 10. Documentation & Changelog

- [ ] 10.1 Update `AGENTS.md` iteration table — add row for Spec 2 frontend work (mark In Progress or Complete as appropriate)
- [ ] 10.2 Append to `CHANGELOG.md` under `[Unreleased]`:
  - Added: `portfolioStore` Zustand slice — persists `activePortfolioId` to localStorage
  - Added: `TopBar` component with `PortfolioSwitcher` and `UserBadge`
  - Added: `EmptyPortfolioGate` for first-time users with no portfolios
  - Added: `useActivePortfolio` and `usePortfolios` hooks
  - Changed: All dashboard pages now read `activePortfolioId` from global context; per-page `AccountFilter` state removed
  - Changed: Sidebar cleaned of sign-out and standalone account-management links
