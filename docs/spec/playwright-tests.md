# Playwright Tests — Overview and Detailed Test Cases (English)

This file lists the Playwright spec files and provides per-test-case short details (preconditions and expected results) in English. The specs live in `frontend/tests/specs`.

## Spec Files

- frontend/tests/specs/auth.spec.ts — Authentication flows (login, register, logout, auth navigation)
- frontend/tests/specs/dashboard.spec.ts — Dashboard overview (metrics, charts, empty state, error/retry)
- frontend/tests/specs/navigation.spec.ts — Sidebar navigation, active states, and logout
- frontend/tests/specs/trades.spec.ts — Trades list and trade detail (table rendering, pagination, empty state)
- frontend/tests/specs/reports.spec.ts — Reports navigation that links into Trades with filters
- frontend/tests/specs/import.spec.ts — Broker import page (account selection, file upload)
- frontend/tests/specs/accounts.spec.ts — Accounts & Integrations (create/edit/delete accounts)
- frontend/tests/specs/features-settings.spec.ts — Feature-flag settings and their UI effects
- frontend/tests/specs/feature-flag-sidebar.spec.ts — Smoke test for feature-gated sidebar items
- frontend/tests/specs/seed.spec.ts — Seed / placeholder test group
- frontend/tests/example.spec.ts — Minimal example tests (can be removed)

## Detailed Test Cases (per TC id)

Auth (frontend/tests/specs/auth.spec.ts)
- TC-001 — Successful login
  - Preconditions: user exists, not authenticated (fresh browser session)
  - Expected: redirect to /dashboard, token stored in localStorage
- TC-002 — Wrong password shows error
  - Preconditions: existing user
  - Expected: error message shown, remain on /login
- TC-003 — Empty form triggers HTML5 validation
  - Preconditions: unauthenticated
  - Expected: browser validation prevents submit; no navigation
- TC-004 — Successful registration
  - Preconditions: username/email not already taken
  - Expected: account created in backend, redirect to /dashboard or /login
- TC-005 — Registration with mismatched password
  - Preconditions: registration form filled with mismatching passwords
  - Expected: validation error displayed; account not created
- TC-006 — Auth page navigation links
  - Preconditions: unauthenticated
  - Expected: "Create one" navigates to /register; "Sign in" navigates to /login

Dashboard (frontend/tests/specs/dashboard.spec.ts)
- TC-030 — Dashboard loads with metrics
  - Preconditions: authenticated user with trades in DB
  - Expected: metrics cards, net P&L label, and charts visible
- TC-031 — MetricsCards show non-zero values
  - Preconditions: seeded trades exist
  - Expected: at least one metric has a non-zero value and is visible
- TC-032 — Equity curve chart visible
  - Expected: chart SVG is present and visible
- TC-033 — Drawdown chart visible
  - Expected: drawdown SVG is present and visible
- TC-035 — Import link in empty state navigates
  - Preconditions: dashboard shows empty state (no trades)
  - Expected: clicking Import navigates to /dashboard/import

Navigation (frontend/tests/specs/navigation.spec.ts)
- TC-040 — Sidebar shows all navigation items
  - Preconditions: authenticated
  - Expected: Trades, Playbooks, Tags, Import and Sign Out visible
- TC-041 — Navigate to Trades
  - Expected: URL contains /dashboard/trades and Trades heading visible
- TC-042 — Navigate to Playbooks
  - Expected: URL contains /dashboard/playbooks and heading visible
- TC-043 — Navigate to Tags
  - Expected: URL contains /dashboard/tags and heading visible
- TC-044 — Navigate to Import
  - Expected: URL contains /dashboard/import and Import Trades heading visible
- TC-045 — Overview link active on /dashboard
  - Expected: overview link has active class (nav-active)
- TC-046 — Active link updates when navigating to Trades
  - Expected: Trades link has active class; Overview link not active
- TC-047 — Sign Out logs out and redirects to /login
  - Expected: redirect to /login; localStorage token cleared
- TC-048 — After logout, /dashboard redirects to /login
  - Expected: direct access to /dashboard redirects to /login

Trades (frontend/tests/specs/trades.spec.ts)
- TC-050 — Page heading and subtitle render
  - Expected: "Trades" heading and subtitle visible
- TC-051 — Table renders all column headers
  - Expected: headers like Symbol, Direction, PnL, Opened At, Closed At visible
- TC-052 — Table shows seeded trades (>= 10 rows)
  - Preconditions: global-setup seeded at least 10 trades
  - Expected: table has >= 10 rows
- TC-053 — Trade rows contain expected symbols
  - Expected: seeded symbol (e.g., AAPL) appears in table cells
- TC-054 — Direction badges (LONG/SHORT) shown
  - Expected: LONG and SHORT badge texts visible in rows
- TC-055 — Previous pagination button disabled on first page
  - Expected: Prev button visible and disabled on initial page
- TC-056 — Next button reflects whether more pages exist
  - Expected: Next button present; disabled if rows < page size, otherwise present
- TC-057 — Clicking symbol navigates to trade detail
  - Expected: navigation to /dashboard/trades/<uuid> and detail main visible
- TC-058 — Empty state message for user with no trades
  - Preconditions: create fresh user with no trades
  - Expected: "No trades found. Import trades to get started." visible
- TC-059 — Pagination buttons disabled in empty state
  - Expected: Prev and Next visible and disabled
- TC-060 — Trade detail page shows trade fields
  - Expected: detail page renders (no 404) and main content visible

Reports (frontend/tests/specs/reports.spec.ts)
- TC-R001 — Hourly report navigation to trades with hour_of_day
  - Expected: after clicking report row, navigate to /dashboard/trades?hour_of_day=N and filter chip present
- TC-R002 — Weekday report navigation (day_of_week)
  - Expected: /dashboard/trades?day_of_week=N and filter chip present
- TC-R003 — Monthly report navigation sets date range
  - Expected: /dashboard/trades with opened_at_from and opened_at_to params
- TC-R004 — Yearly report navigation sets full-year range
  - Expected: /dashboard/trades with opened_at_from/to params covering year
- TC-R005/006 — After navigation, Filters button shows "1" active
  - Expected: Filters button contains count '1'
- TC-R007 — Calendar report day click navigates with closed_at range and filter count
  - Expected: /dashboard/trades with closed_at_from/to and Filters shows count '2'

Import (frontend/tests/specs/import.spec.ts)
- TC-070 — Page renders heading and subtitle
  - Expected: "Import Trades" heading and upload instructions visible
- TC-071 — Step 1 account selector visible
  - Expected: account combobox present
- TC-072 — Account selector includes seeded E2E account
  - Preconditions: .auth/seed-state.json contains seeded accountId
  - Expected: seeded account appears as option in combobox
- TC-073 — Selecting account shows Step 2
  - Expected: Step 2 content (Import Trades) becomes visible after selecting account
- TC-074 — File upload section reachable after account selection
  - Expected: file upload UI visible (input[type=file] or upload section)
- TC-075 — Upload button absent before file selected
  - Expected: no "Import N file(s)" button present before file selection
- TC-076 — Successful IBKR import shows per-file result
  - Preconditions: IBKR fixture exists in tests/fixtures
  - Expected: after upload, UI shows created/skipped/Import complete or error message

Accounts (frontend/tests/specs/accounts.spec.ts)
- TC-080 — Accounts tab renders with New Account button
  - Expected: "+ New Account" button visible on Accounts & Integrations tab
- TC-081 — Create a manual account
  - Expected: newly created manual account row appears and can be deleted
- TC-082 — Create IBKR account with credentials
  - Expected: credential fields appear, account row created, API credential indicator visible
- TC-083 — Credential fields toggle on type change
  - Expected: switching account type shows/hides IBKR/Schwab specific fields
- TC-084 — Create a Schwab account
  - Expected: Schwab account row appears and can be deleted
- TC-085 — Edit existing account name
  - Expected: edited account name saved and visible in list
- TC-086 — Delete account removes it from list
  - Expected: deleted account no longer visible after reload

Feature Flags (frontend/tests/specs/features-settings.spec.ts)
- enabling a feature flag and Apply persists across reloads
  - Preconditions: authenticated
  - Expected: toggling + Apply stores settings; reloading keeps flags enabled
- enabling multiple flags in sequence does not reset earlier changes
  - Expected: flags remain enabled after subsequent changes and apply
- enabling Cash & Dividends / Cash Report makes nav items appear
  - Expected: sidebar links for Cash & Dividends and Cash Report are visible
- immediate sidebar update without navigation (regression test)
  - Expected: sidebar updates with new items without requiring a page navigation
- disabling flags hides sidebar items
  - Expected: after disabling and applying, sidebar items are hidden

Feature Flag Sidebar Smoke (frontend/tests/specs/feature-flag-sidebar.spec.ts)
- smoke test enabling flags via API shows links
  - Expected: after API toggle + reload, Cash & Dividends and Cash Report links visible; cleanup resets flags

Seed / Example
- seed.spec.ts — placeholder seed tests (no assertions)
- example.spec.ts — lightweight examples against playwright.dev (can be removed)

## Notes
- Many tests rely on `global-setup` and seeded data. See `frontend/tests/TESTPLAN.md` for local setup steps.
- Some tests run serially to avoid state races (feature flags, certain empty-state scenarios).
