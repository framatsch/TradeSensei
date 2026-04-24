## 0. Prerequisites (blocking — verify before starting)

- [ ] 0.1 Confirm Spec 1 (`portfolio-core-data-model`) is applied: `GET /api/v1/portfolios` returns HTTP 200
- [ ] 0.2 Confirm Spec 2 (`app-state-topbar-navigation`) is applied: `useActivePortfolio` hook is importable and `activePortfolioId` is in the Zustand store
- [ ] 0.3 Run `openapi-sync` skill to ensure the generated TypeScript client is current (needed for portfolio API calls in new components)

## 1. Backend — Chart Display Settings

- [ ] 1.1 Add three new typed fields to `UserSettingsRead` in `backend/app/schemas/user.py`:
  - `chart_candles_before: int = Field(default=20, ge=1)`
  - `chart_candles_after: int = Field(default=10, ge=1)`
  - `chart_show_post_exit: bool = Field(default=False)`
- [ ] 1.2 Add the same three fields (all `| None`, default `None`) to `UserSettingsUpdate` in `backend/app/schemas/user.py` with the same `ge=1` validator on the int fields
- [ ] 1.3 Update the settings reader in `backend/app/api/v1/users.py` (the `GET /me/settings` handler) to pull `"chart_candles_before"`, `"chart_candles_after"`, `"chart_show_post_exit"` from `user_settings` rows and include them in the `UserSettingsRead` response with their defaults when the keys are absent
- [ ] 1.4 Update the settings writer in `backend/app/api/v1/users.py` (the `PUT /me/settings` handler) to upsert the three new keys when they are present in the request body
- [ ] 1.5 Run `lint-check` skill and fix any ruff / mypy errors introduced in steps 1.1–1.4

## 2. Backend — Tests

- [ ] 2.1 Add unit tests for the `GET /me/settings` endpoint: verify that missing keys return default values `20`, `10`, `false` respectively
- [ ] 2.2 Add unit tests for the `PUT /me/settings` endpoint: write all three fields; read them back; verify values match
- [ ] 2.3 Add unit test: partial update (only `chart_candles_before`) does not clobber the other two keys
- [ ] 2.4 Add unit test: `chart_candles_before = 0` or negative value is rejected with HTTP 422

## 3. Frontend — Settings Page: New Tabs

- [ ] 3.1 Read `frontend/app/dashboard/settings/SettingsPageClient.tsx` in full before editing
- [ ] 3.2 Extend `Tab` type to `"general" | "integrations" | "corporate-actions" | "features" | "portfolios" | "playbooks-tags" | "look-and-feel"`
- [ ] 3.3 Add three entries to the `TABS` array: `{ id: "portfolios", label: "Portfolios" }`, `{ id: "playbooks-tags", label: "Playbooks & Tags" }`, `{ id: "look-and-feel", label: "Look & Feel" }`
- [ ] 3.4 Extend the `useEffect` that reads `?tab=` query param to handle `"portfolios"`, `"playbooks-tags"`, and `"look-and-feel"` values
- [ ] 3.5 Import and render `<PortfolioSettings />`, `<PlaybooksTagsSettings />`, `<ChartDisplaySettings />` in the tab content section

## 4. Frontend — PortfolioSettings Component

- [ ] 4.1 Create `frontend/components/settings/PortfolioSettings.tsx` — client component; use `usePortfolios()` (Spec 2) to load the list
- [ ] 4.2 Render a list of portfolio cards: show name, currency, live/paper badge, and colour dot; add Edit and Delete buttons per card
- [ ] 4.3 Implement inline Create form (name input, currency select with allowlist: USD/EUR/GBP/JPY/CHF/CAD/AUD, is_paper toggle, colour picker); on submit call `createPortfolioApiV1PortfoliosPost` from generated client
- [ ] 4.4 Implement inline Edit form: same fields as Create; `base_currency` select is disabled with a tooltip when `has_trades` is true (call `GET /api/v1/portfolios/{id}` to check, or derive from whether the portfolio has accounts with trade count); on submit call `updatePortfolioApiV1PortfoliosPortfolioIdPatch`
- [ ] 4.5 Implement Delete confirmation: show a small confirm popover; on confirm call `deletePortfolioApiV1PortfoliosPortfolioIdDelete`; show inline error if backend returns 409 ("Remove all accounts first")
- [ ] 4.6 Implement **Danger Zone** section at the bottom of the component:
  - "Wipe Portfolio Data" button opens a modal dialog
  - Modal shows warning copy and a text input labelled "Type portfolio name to confirm"
  - Confirm button is disabled until the typed value exactly matches the portfolio name (case-sensitive)
  - On confirm: iterate `activePortfolio.accounts` (loaded via `useAccounts(portfolioId)`), call `freshStartImport` for each account sequentially, show per-account progress indicator and final summary toast
- [ ] 4.7 Handle loading and error states: skeleton cards while fetching; error banner if portfolio list fetch fails
- [ ] 4.8 Invalidate `["portfolios"]` React Query cache after create/update/delete operations

## 5. Frontend — PlaybooksTagsSettings Component

- [ ] 5.1 Create `frontend/components/settings/PlaybooksTagsSettings.tsx` — client component
- [ ] 5.2 Render a two-section layout: "Playbooks" section containing `<PlaybookList />`, "Tags" section containing `<TagList />`; no changes to the existing components needed
- [ ] 5.3 Add a brief explanatory header per section (e.g. "Strategies you can attach to trades" / "Labels for categorising trades")

## 6. Frontend — ChartDisplaySettings Component

- [ ] 6.1 Create `frontend/components/settings/ChartDisplaySettings.tsx` — client component; call `useSettings()` to load current values
- [ ] 6.2 Render a form with:
  - Number input "Candles before entry" bound to `chart_candles_before` (min 1, integer only)
  - Number input "Candles after exit" bound to `chart_candles_after` (min 1, integer only)
  - Toggle/switch "Show post-exit candles by default" bound to `chart_show_post_exit`
- [ ] 6.3 Implement client-side validation: inputs ≤ 0 or non-integer show inline error "Must be a positive whole number"; Save button disabled while invalid
- [ ] 6.4 On save call `useUpdateSettings()` mutation with the three fields; show success toast on resolve; on reject show error toast and revert form state to last saved values
- [ ] 6.5 Show a skeleton / disabled form while the initial settings fetch is loading

## 7. Frontend — AccountSettings: Scope to Active Portfolio

- [ ] 7.1 Read `frontend/components/settings/AccountSettings.tsx` in full before editing
- [ ] 7.2 Import `useActivePortfolio` from `@/hooks/useActivePortfolio`
- [ ] 7.3 Extract `activePortfolioId` from the hook; pass it to `useAccounts(portfolioId)` (update the hook signature if needed to accept optional `portfolioId`)
- [ ] 7.4 Update `AccountForm` default values: when `activePortfolioId` is set, pre-populate `portfolio_id` with it
- [ ] 7.5 In fallback mode (no `activePortfolioId`): render a notice "Showing all accounts — select a portfolio to filter" above the account list; each row shows its portfolio name

## 8. Frontend — Remove Standalone Sidebar Pages and Nav Links

- [ ] 8.1 Replace `frontend/app/dashboard/playbooks/page.tsx` body with `redirect('/dashboard/settings?tab=playbooks-tags')` using Next.js `redirect()` from `'next/navigation'`
- [ ] 8.2 Replace `frontend/app/dashboard/tags/page.tsx` body with `redirect('/dashboard/settings?tab=playbooks-tags')` using Next.js `redirect()` from `'next/navigation'`
- [ ] 8.3 Read `frontend/app/dashboard/layout.tsx` in full; locate the "Playbooks" and "Tags" sidebar nav items and remove them
- [ ] 8.4 Verify no other component imports from the removed page files (run `rg "dashboard/playbooks" frontend/` and `rg "dashboard/tags" frontend/` — redirects and any remaining references should be valid)

## 9. Frontend — TypeScript Build Verification

- [ ] 9.1 Run `npm run build` in `frontend/` and fix all TypeScript errors and Next.js build warnings

## 10. Tests

- [ ] 10.1 Update any existing unit tests that reference the `Tab` type or `TABS` array in `SettingsPageClient.tsx`
- [ ] 10.2 Write unit test for `ChartDisplaySettings`: renders saved values; shows validation error on ≤ 0 input; calls `useUpdateSettings` on valid save
- [ ] 10.3 Write unit test for `PortfolioSettings`: renders portfolio list; create form calls API; delete confirmation blocks with 409 error message
- [ ] 10.4 Write unit test for `PlaybooksTagsSettings`: renders both sections; `PlaybookList` and `TagList` are present in the DOM
- [ ] 10.5 Update any Playwright E2E tests that previously navigated to `/dashboard/playbooks` or `/dashboard/tags` — update them to navigate to `/dashboard/settings?tab=playbooks-tags`
- [ ] 10.6 Add Playwright E2E test: navigate to `/dashboard/playbooks` → verify redirect to Settings → verify Playbooks & Tags tab is active

## 11. OpenAPI Sync & Lint

- [ ] 11.1 Run `openapi-sync` skill to regenerate TypeScript client after backend schema changes
- [ ] 11.2 Run `lint-check` skill — fix any remaining ruff / mypy / TypeScript errors
- [ ] 11.3 Run `unit-test` skill — verify all backend tests pass

## 12. Documentation & Changelog

- [ ] 12.1 Append to `CHANGELOG.md` under `[Unreleased]`:
  - Added: Look & Feel settings tab — chart display defaults (`chart_candles_before`, `chart_candles_after`, `chart_show_post_exit`) stored in user settings
  - Added: Portfolios tab in Settings — full CRUD for portfolios with Danger Zone (data wipe)
  - Added: Playbooks & Tags tab in Settings — consolidated management; standalone sidebar pages removed
  - Changed: Accounts & Integrations tab scoped to active portfolio (Spec 2 prerequisite)
  - Changed: `/dashboard/playbooks` and `/dashboard/tags` now redirect to `/dashboard/settings?tab=playbooks-tags`
  - Changed: `UserSettingsRead` / `UserSettingsUpdate` schemas gain three new chart display fields
