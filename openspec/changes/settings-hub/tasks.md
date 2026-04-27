## 0. Prerequisites (blocking — verify before starting)

- [x] 0.1 Confirm Spec 1 (`portfolio-core-data-model`) is applied: `GET /api/v1/portfolios` returns HTTP 200
- [x] 0.2 Confirm Spec 2 (`app-state-topbar-navigation`) is applied: `useActivePortfolio` hook is importable and `activePortfolioId` is in the Zustand store
- [x] 0.3 Run `openapi-sync` skill to ensure the generated TypeScript client is current (needed for portfolio API calls in new components)

## 1. Backend — Chart Display Settings, Default Portfolio & Home Route

- [x] 1.1 Add five new typed fields to `UserSettingsRead` in `backend/app/schemas/user.py`:
  - `chart_candles_before: int = Field(default=20, ge=1)`
  - `chart_candles_after: int = Field(default=10, ge=1)`
  - `chart_show_post_exit: bool = Field(default=False)`
  - `default_portfolio_id: UUID | None = Field(default=None)`
  - `home_route: Literal["/dashboard", "/dashboard/trades", "/dashboard/library"] = Field(default="/dashboard")`
- [x] 1.2 Add the same five fields (all optional, `| None`, default `None`) to `UserSettingsUpdate`; int fields keep `ge=1` validator; `home_route` field keeps the same `Literal` allowlist
- [x] 1.3 Update the settings reader in `backend/app/api/v1/users.py` (`GET /me/settings`) to pull all five new keys from `user_settings` rows; return defaults when keys are absent; if the stored `home_route` value is not in the allowlist treat it as `"/dashboard"`
- [x] 1.4 Update the settings writer in `backend/app/api/v1/users.py` (`PUT /me/settings`) to upsert the five new keys when present in the request body
- [x] 1.5 Run `lint-check` skill and fix any ruff / mypy errors introduced in steps 1.1–1.4

## 2. Backend — Tests

- [x] 2.1 `GET /me/settings`: verify missing keys return defaults `20`, `10`, `false`, `null`, `"/dashboard"`
- [x] 2.2 `PUT /me/settings`: write all five fields; read back; verify values match
- [x] 2.3 Partial update (only `chart_candles_before`) does not clobber the other four keys
- [x] 2.4 `chart_candles_before = 0` or negative rejected with HTTP 422
- [x] 2.5 `default_portfolio_id` set to a valid UUID string; read back; verify stored correctly
- [x] 2.6 `home_route` set to `"/dashboard/trades"`; read back correctly
- [x] 2.7 `home_route` with an invalid value (e.g. `"/dashboard/invalid"`) rejected with HTTP 422

## 3. Frontend — Settings Page: New Tabs

- [x] 3.1 Read `frontend/app/dashboard/settings/SettingsPageClient.tsx` in full before editing
- [x] 3.2 Extend `Tab` type to `"general" | "integrations" | "corporate-actions" | "features" | "portfolios" | "look-and-feel"` (no `"playbooks-tags"` — Playbooks/Tags are in Library context)
- [x] 3.3 Add two entries to the `TABS` array: `{ id: "portfolios", label: "Portfolios" }`, `{ id: "look-and-feel", label: "Look & Feel" }`
- [x] 3.4 Extend the `useEffect` that reads `?tab=` query param to handle `"portfolios"` and `"look-and-feel"` values
- [x] 3.5 Import and render `<PortfolioSettings />` and `<ChartDisplaySettings />` in the tab content section (NOT `<PlaybooksTagsSettings />`)

## 4. Frontend — PortfolioSettings Component

- [ ] 4.1 Create `frontend/components/settings/PortfolioSettings.tsx` — client component; use `usePortfolios()` (Spec 2) and `useSettings()` to load list and `default_portfolio_id`
- [ ] 4.2 Render portfolio cards: show colour chip, name, currency, default indicator (filled star if `id === default_portfolio_id`), Edit and Delete buttons
- [ ] 4.3 Define `PORTFOLIO_COLORS: string[]` constant (12 hex values including `'#6366f1'`) in `frontend/lib/constants/portfolioColors.ts`; reuse in both create and edit forms
- [ ] 4.4 Implement inline Create form:
  - Name input (required)
  - Currency select (allowlist: USD/EUR/GBP/CHF/JPY/AUD/CAD)
  - Colour chip picker: row of 12 `<button>` elements, each a filled circle (20 px); active chip shows a ring; clicking sets `color_hex`; default pre-selected chip is `'#6366f1'`
  - On submit: call `createPortfolioApiV1PortfoliosPost`
- [ ] 4.5 Implement inline Edit form: same fields as Create; `base_currency` select disabled with tooltip when `has_trades` is true; on submit call `updatePortfolioApiV1PortfoliosPortfolioIdPatch`
- [ ] 4.6 Implement "Set as default" action per portfolio card:
  - Star icon button (unfilled = not default, filled = default)
  - On click: call `PUT /api/v1/users/me/settings` with `{ default_portfolio_id: portfolio.id }`; invalidate `["settings"]` cache; update star states in the list optimistically
- [ ] 4.7 Implement Delete confirmation: confirm popover; on confirm call `deletePortfolioApiV1PortfoliosPortfolioIdDelete`; inline 409 error "Remove all accounts before deleting this portfolio"
- [ ] 4.8 Implement **Danger Zone** section at the bottom:
  - "Wipe Portfolio Data" button opens modal dialog
  - Modal: warning copy + text input "Type portfolio name to confirm"
  - Confirm button disabled until typed name matches exactly (case-sensitive)
  - On confirm: iterate accounts via `useAccounts(portfolioId)`, call `freshStartImport` per account sequentially, show per-account progress + final summary toast
- [ ] 4.9 Handle loading / error states: skeleton cards while fetching; error banner on failure
- [ ] 4.10 Invalidate `["portfolios"]` React Query cache after create/update/delete

## 5. Frontend — PlaybooksTagsSettings Component

**SKIPPED** — Playbooks and Tags are managed in the Global Library context (Spec 2 tasks 7.1–7.3).
No `PlaybooksTagsSettings.tsx` component is created in this spec.

## 6. Frontend — ChartDisplaySettings Component

- [x] 6.1 Create `frontend/components/settings/ChartDisplaySettings.tsx` — client component; call `useSettings()` to load current values
- [x] 6.2 Render a form with:
  - Number input "Candles before entry" bound to `chart_candles_before` (min 1, integer only)
  - Number input "Candles after exit" bound to `chart_candles_after` (min 1, integer only)
  - Toggle/switch "Show post-exit candles by default" bound to `chart_show_post_exit`
  - Select "Default Home Page" bound to `home_route` with three options: "Portfolio Overview" → `"/dashboard"`, "Journal" → `"/dashboard/trades"`, "Strategy & Tags" → `"/dashboard/library"`
- [x] 6.3 Implement client-side validation: number inputs ≤ 0 or non-integer show inline error "Must be a positive whole number"; Save button disabled while invalid
- [x] 6.4 On save call `useUpdateSettings()` mutation with all four fields (`chart_candles_before`, `chart_candles_after`, `chart_show_post_exit`, `home_route`); show success toast on resolve; on reject show error toast and revert form state to last saved values; invalidate `["users","me","settings"]` cache so the TopBar wordmark link updates immediately
- [x] 6.5 Show a skeleton / disabled form while the initial settings fetch is loading

## 7. Frontend — AccountSettings: Scope to Active Portfolio

- [ ] 7.1 Read `frontend/components/settings/AccountSettings.tsx` in full before editing
- [ ] 7.2 Import `useActivePortfolio` from `@/hooks/useActivePortfolio`
- [ ] 7.3 Extract `activePortfolioId` from the hook; pass it to `useAccounts(portfolioId)` (update the hook signature if needed to accept optional `portfolioId`)
- [ ] 7.4 Update `AccountForm` default values: when `activePortfolioId` is set, pre-populate `portfolio_id` with it
- [ ] 7.5 In fallback mode (no `activePortfolioId`): render a notice "Showing all accounts — select a portfolio to filter" above the account list; each row shows its portfolio name

## 8. Frontend — Route Redirects (handled by Spec 2)

These tasks are owned by Spec 2 (`app-state-topbar-navigation`) task list items 7.5 and 7.6.
They are listed here for cross-reference only — do NOT duplicate them.

- Spec 2 task 7.5: `/dashboard/playbooks` → `redirect('/dashboard/library/playbooks')`
- Spec 2 task 7.6: `/dashboard/tags` → `redirect('/dashboard/library/tags')`
- Spec 2 task 8.7: Sidebar Playbooks/Tags nav items removed from portfolio sidebar

## 9. Frontend — TypeScript Build Verification

- [ ] 9.1 Run `npm run build` in `frontend/` and fix all TypeScript errors and Next.js build warnings

## 10. Tests

- [ ] 10.1 Update any existing unit tests that reference the `Tab` type or `TABS` array in `SettingsPageClient.tsx` (now 6 tabs, not 7)
- [ ] 10.2 Unit test `ChartDisplaySettings`: renders saved values; validation error on ≤ 0 input; calls `useUpdateSettings` on valid save
- [ ] 10.3 Unit test `PortfolioSettings`:
  - renders portfolio list with colour chips and default indicator
  - create form submits with selected colour chip `color_hex`
  - delete confirmation blocks with 409 error message
  - "Set as default" star click calls `PUT /me/settings` with `default_portfolio_id`
  - default indicator appears on correct portfolio card
- [ ] 10.4 Unit test: colour chip picker — only one chip active at a time; clicking new chip deselects previous
- [ ] 10.5 Playwright: `frontend/tests/specs/portfolio-settings.spec.ts` — **ALREADY WRITTEN** (TC-130–TC-170); covers:
  - Portfolio CRUD (create, duplicate name error, edit rename, delete 409)
  - Colour chip picker (12 chips shown, one active at a time, hex submitted)
  - Default portfolio selector (star toggle, mutual exclusion, user_settings updated, used as fallback)
  - Danger Zone (exact name match required, case-sensitive, Confirm stays disabled until match)
  - base_currency immutability (field disabled + tooltip when has_trades)

## 11. OpenAPI Sync & Lint

- [ ] 11.1 Run `openapi-sync` skill to regenerate TypeScript client after backend schema changes
- [ ] 11.2 Run `lint-check` skill — fix any remaining ruff / mypy / TypeScript errors
- [ ] 11.3 Run `unit-test` skill — verify all backend tests pass

## 12. Documentation & Changelog

- [ ] 12.1 Append to `CHANGELOG.md` under `[Unreleased]`:
  - Added: Portfolios tab in Settings — full CRUD for portfolios with colour chip picker, default portfolio selector, and Danger Zone (data wipe)
  - Added: Look & Feel settings tab — chart display defaults (`chart_candles_before`, `chart_candles_after`, `chart_show_post_exit`) stored in user settings
  - Changed: Accounts & Integrations tab scoped to active portfolio (Spec 2 prerequisite)
  - Changed: `UserSettingsRead` / `UserSettingsUpdate` schemas gain four new fields (3 chart display + `default_portfolio_id`)
  - Note: Playbooks & Tags management moved to Global Library context (Spec 2) — no Settings tab
