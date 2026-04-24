## 0. Prerequisites (blocking — verify before starting)

- [ ] 0.1 Confirm Spec 1 (`portfolio-core-data-model`) backend changes are merged and deployed to the dev environment
- [ ] 0.2 Run `openapi-sync` skill to regenerate the TypeScript client after Spec 1; verify `listPortfoliosApiV1PortfoliosGet` and related functions appear in `frontend/lib/api/`
- [ ] 0.3 Verify Zustand v5 is available (`"zustand": "^5.0.11"` in `frontend/package.json`) — no install needed

## 1. Application Context Zustand Store

- [ ] 1.1 Create `frontend/stores/appContextStore.ts` — define `AppContext = 'portfolio' | 'library' | 'checkin'`; define `AppContextState` interface with `activeContext: AppContext`, `hydrated: boolean`, `setActiveContext(ctx: AppContext): void`, `hydrate(): void`
- [ ] 1.2 Implement `hydrate()`: wrap `localStorage.getItem("active_app_context")` in `try/catch`; validate value is one of the three valid contexts; default to `'portfolio'` if absent or invalid; always set `hydrated = true`
- [ ] 1.3 Implement `setActiveContext()`: update store AND call `localStorage.setItem("active_app_context", ctx)` in `try/catch`
- [ ] 1.4 Export `useAppContextStore` hook; create thin wrapper `frontend/hooks/useAppContext.ts` returning `{ activeContext, setActiveContext }` — pages use the hook, not the store directly

## 2. Portfolio Zustand Store

- [ ] 2.1 Create `frontend/stores/portfolioStore.ts` — define `PortfolioState` interface with `activePortfolioId: string | null`, `hydrated: boolean`, `setActivePortfolioId(id: string): void`, `clearActivePortfolioId(): void`, `hydrate(): void`
- [ ] 2.2 Implement `hydrate()`: wrap `localStorage.getItem("active_portfolio_id")` in `try/catch`; always set `hydrated = true`
- [ ] 2.3 Implement `setActivePortfolioId()`: update store AND `localStorage.setItem` in `try/catch`
- [ ] 2.4 Implement `clearActivePortfolioId()`: set `activePortfolioId = null` and `localStorage.removeItem` in `try/catch`
- [ ] 2.5 Export `usePortfolioStore` hook from `frontend/stores/portfolioStore.ts`

## 3. Portfolio Hooks

- [ ] 3.1 Create `frontend/hooks/usePortfolios.ts` — wrap `listPortfoliosApiV1PortfoliosGet` with TanStack Query key `["portfolios"]`, staleTime 60 000 ms; return `{ portfolios: PortfolioRead[], isLoading, isError }`
- [ ] 3.2 Create `frontend/hooks/useActivePortfolio.ts` — implement `useActivePortfolio()` hook:
  - Read `activePortfolioId` and `hydrated` from `usePortfolioStore`
  - Call `usePortfolios()` for the list
  - Resolve active portfolio (cross-reference by id)
  - Stale-ID fallback: if stored ID not in list AND list non-empty → prefer `default_portfolio_id` from `user_settings` if set; otherwise use `portfolios[0].id`; call `setActivePortfolioId(resolvedId)`
  - Empty list: call `clearActivePortfolioId()`
  - Set `isLoading = !hydrated || portfoliosQuery.isLoading`
  - Return `{ activePortfolioId, activePortfolio, portfolios, isLoading, setActivePortfolio }`
- [ ] 3.3 Call both `appContextStore.hydrate()` and `portfolioStore.hydrate()` in `frontend/app/providers.tsx` inside `useEffect` on mount (client-side only)

## 4. BentoMenu Component

- [ ] 4.1 Create `frontend/components/layout/BentoMenu.tsx` — renders a nine-dot grid icon button (`Grid3x3` from lucide-react or equivalent); on click opens a Radix UI `Popover` (modal={false}) listing three context entries
- [ ] 4.2 Each BentoMenu entry shows: icon, label (Portfolio Workspace / Global Library / Market Check-in), active indicator (filled dot) when `activeContext` matches
- [ ] 4.3 On entry click: call `setActiveContext(ctx)`, close popover, navigate to context root route (`/dashboard`, `/dashboard/library`, `/dashboard/checkin`)
- [ ] 4.4 Market Check-in entry navigates to `/dashboard/checkin` which shows a placeholder — label it "Coming Soon" with a subdued style (no badge, slight opacity)

## 5. TopBar Component

- [ ] 5.1 Create `frontend/components/layout/TopBar.tsx` — full-width `<header>` (`h-14`, sticky, `border-b bg-background z-40`); left: `<SidebarToggle />` + `<BentoMenu />` + `<wordmark as Link>`; center: context-aware slot (see 5.2); right: `<UserBadge />`; the `SidebarToggle` button calls the same `toggleSidebar` handler currently used by the floating `PanelLeftOpen` button and the sidebar's `PanelLeftClose` button — pass it down as a prop from `DashboardLayout`
- [ ] 5.2 Center slot logic: read `activeContext` from `useAppContext()`; if `activeContext === 'portfolio'` render `<PortfolioSwitcher />`; otherwise render `null`
- [ ] 5.3 Create `frontend/components/layout/PortfolioSwitcher.tsx` — trigger button showing `[colour chip] [name] ([currency]) [LIVE|PAPER badge] [▼]`; on click opens Radix UI `DropdownMenu`; each item shows colour chip, name, currency code, LIVE/PAPER badge, checkmark if active; calls `setActivePortfolio(id)` on select; renders skeleton when `isLoading`
- [ ] 5.4 Create `frontend/components/layout/UserBadge.tsx` — initials avatar (first char `first_name` + first char `last_name`; fallback first 2 chars of email; uppercased); background derived from user `id` via HSL hash; on click opens Radix UI `DropdownMenu` with five items in order: "Settings" (`/dashboard/settings`), "Help" (`window.open('/help', ...)` — same params as current sidebar Help button), "About v{version}" (reads `process.env.NEXT_PUBLIC_APP_VERSION`, opens `AboutModal`), visual `<DropdownMenuSeparator />`, "Sign Out" (calls `useLogout()`)
- [ ] 5.5 Implement wordmark as home-link: read `home_route` from `useSettings()` data (key `home_route`, default `"/dashboard"`); render wordmark as `<Link href={homeRoute}>Trade Sensei</Link>`; import `useSettings` hook (already exists at `frontend/hooks/useSettings.ts`)

## 6. EmptyPortfolioGate Component

- [ ] 6.1 Create `frontend/components/layout/EmptyPortfolioGate.tsx` — centred card with icon, heading ("No portfolios yet"), description, and primary CTA "Create your first portfolio" navigating to `/dashboard/settings?tab=portfolios`; TopBar is still rendered above the gate

## 7. Library and Check-in Routes

- [ ] 7.1 Create `frontend/app/dashboard/library/page.tsx` — immediately redirects to `/dashboard/library/playbooks`
- [ ] 7.2 Create `frontend/app/dashboard/library/playbooks/page.tsx` — renders the existing `PlaybookList` component; sets `activeContext = 'library'` on mount if not already set
- [ ] 7.3 Create `frontend/app/dashboard/library/tags/page.tsx` — renders the existing `TagList` component
- [ ] 7.4 Create `frontend/app/dashboard/checkin/page.tsx` — renders a "Market Check-in — Coming Soon" placeholder card; sets `activeContext = 'checkin'` on mount
- [ ] 7.5 Replace body of `frontend/app/dashboard/playbooks/page.tsx` with `redirect('/dashboard/library/playbooks')` using Next.js `redirect()` from `'next/navigation'`
- [ ] 7.6 Replace body of `frontend/app/dashboard/tags/page.tsx` with `redirect('/dashboard/library/tags')`

## 8. Dashboard Layout Integration

- [ ] 8.1 Read `frontend/app/dashboard/layout.tsx` in full before editing
- [ ] 8.2 Add CSS variable `--topbar-height: 3.5rem` to the layout root; update sidebar `top-0` → `top-[var(--topbar-height)]` and `h-screen` → `h-[calc(100vh-var(--topbar-height))]`
- [ ] 8.3 Insert `<TopBar />` as the first child of the layout's outermost `<div>`, above sidebar and `<main>` wrapper
- [ ] 8.4 Remove the existing mobile-only hamburger + logo bar (`<header className="... lg:hidden ...">` block at layout.tsx ~line 768) AND remove the floating `PanelLeftOpen` desktop button (`<button className="hidden lg:flex absolute top-4 left-4 ...">` block at ~line 757) — both are replaced by the `SidebarToggle` inside `<TopBar />`
- [ ] 8.5 Remove "Sign Out" nav item from sidebar bottom
- [ ] 8.6 Remove any standalone "Accounts" sidebar nav link
- [ ] 8.7 Remove the "Help" button from the sidebar bottom section — it moves to the UserBadge dropdown (task 5.4)
- [ ] 8.7 Remove "Playbooks" and "Tags" nav items from the portfolio sidebar nav list (they now live in Library context)
- [ ] 8.8 Make sidebar nav-items conditional on `activeContext` (read from `useAppContext()`):
  - `portfolio`: Dashboard, Journal, Reports, Quick Import
  - `library`: Playbooks, Tags
  - `checkin`: Timeline (disabled placeholder item)
- [ ] 8.9 Add a static context-label header above the nav items in each context: `"— WORKSPACE —"` / `"— LIBRARY —"` / `"— CHECK-IN —"`; style as `px-4 pt-3 pb-1 text-xs text-muted-foreground uppercase tracking-widest select-none`
- [ ] 8.9 Add `EmptyPortfolioGate` conditional (portfolio context only): if `!isLoading && portfolios.length === 0` render `<EmptyPortfolioGate />`; if `isLoading` render skeleton; if `portfolios.length > 0` render `{children}`
- [ ] 8.10 Add portfolio fetch error banner: if `usePortfolios()` returns `isError === true` in portfolio context render `"Failed to load portfolios — please refresh"` instead of gate
- [ ] 8.11 Update `<main>` top padding to `pt-14` or the CSS variable

## 9. Page Migrations — Remove Per-Page AccountFilter State

- [ ] 9.1 `frontend/app/dashboard/page.tsx` (Overview) — remove `accountId` state; pass `activePortfolioId` from `useActivePortfolio()` to `useMetrics()`
- [ ] 9.2 `frontend/app/dashboard/analytics/page.tsx` — remove `accountId` state and `<AccountFilter>`; pass `activePortfolioId` to `useReportData()`
- [ ] 9.3 `frontend/app/dashboard/reports/calendar/page.tsx` — remove `accountId` state and `<AccountFilter>`; pass `activePortfolioId` to calendar data hook
- [ ] 9.4 `frontend/app/dashboard/cash/CashPageClient.tsx` — remove `accountId` state and `<AccountFilter>`; pass `activePortfolioId` to cash hooks
- [ ] 9.5 `frontend/app/dashboard/trades/page.tsx` — remove `account_id` query-param logic; accept `portfolioId` from `useActivePortfolio()`
- [ ] 9.6 `rg "AccountFilter" frontend/` — migrate any remaining usages

## 10. Hook Updates — Accept portfolioId

- [ ] 10.1 Update `frontend/hooks/useMetrics.ts` to accept `portfolioId: string`
- [ ] 10.2 Update `frontend/hooks/useEquityCurve.ts` and `useDrawdown.ts` similarly
- [ ] 10.3 Update `frontend/hooks/useAccounts.ts` to accept optional `portfolioId`
- [ ] 10.4 Update `frontend/hooks/useTrades.ts` to accept `portfolioId`

## 11. Cleanup

- [ ] 11.1 If `AccountFilter.tsx` is unused after step 9.6, add JSDoc `/** @deprecated — replaced by global portfolio context */`
- [ ] 11.2 Run `npm run build` in `frontend/` and fix all TypeScript errors

## 12. Tests

- [ ] 12.1 Unit test `appContextStore`: hydration from localStorage, invalid stored value defaults to 'portfolio', setActiveContext persists
- [ ] 12.2 Unit test `portfolioStore`: hydration, stale-ID fallback (respects `default_portfolio_id` from user settings when present), localStorage unavailable
- [ ] 12.3 Unit test `useActivePortfolio`: empty list → gate, stale ID → fallback, loading states
- [ ] 12.4 Playwright: update `navigation.spec.ts` — remove TC-042/TC-043 (Playbooks/Tags now in library), remove TC-047/TC-048 (Sign Out in UserBadge), update TC-040 to remove sidebar Playbooks/Tags/Sign Out assertions. Migration comments already added to the file.
- [ ] 12.5 Playwright: `frontend/tests/specs/topbar-navigation.spec.ts` — **ALREADY WRITTEN** (TC-060–TC-098); covers TopBar visibility, BentoMenu context switching, PortfolioSwitcher context-awareness, sidebar nav per context, redirect from old Playbooks/Tags URLs, UserBadge Sign Out
- [ ] 12.6 Playwright: `frontend/tests/specs/portfolio-context.spec.ts` — **ALREADY WRITTEN** (TC-100–TC-121); covers localStorage persistence, stale-ID fallback, appContextStore persistence, EmptyPortfolioGate (shown on empty list, CTA, TopBar visible, no sidebar, loading skeleton, error banner NOT showing gate), AccountFilter removal

## 13. Documentation & Changelog

- [ ] 13.1 Update `AGENTS.md` iteration table for Spec 2 frontend work
- [ ] 13.2 Append to `CHANGELOG.md` under `[Unreleased]`:
  - Added: `appContextStore` Zustand slice — Portfolio Workspace / Global Library / Market Check-in mode, persisted to localStorage
  - Added: `portfolioStore` Zustand slice — persists `activePortfolioId` to localStorage
  - Added: `TopBar` with `BentoMenu` (nine-dot context switcher), context-aware `PortfolioSwitcher` (colour chip + name), and `UserBadge`
  - Added: `EmptyPortfolioGate` for first-time users with no portfolios
  - Added: Global Library context at `/dashboard/library` (Playbooks, Tags)
  - Added: Market Check-in placeholder at `/dashboard/checkin`
  - Changed: All dashboard pages read `activePortfolioId` from global context; per-page `AccountFilter` state removed
  - Changed: Sidebar nav-items are context-specific; Playbooks/Tags moved to Library context
  - Changed: Sidebar cleaned of sign-out and standalone account-management links
