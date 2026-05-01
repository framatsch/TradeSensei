## 1. Settings Tab Refactor

- [ ] 1.1 In `SettingsPageClient.tsx`, add a new `portfolios-brokers` tab type and replace the separate `portfolios` and `integrations` tab entries with a single "Portfolios & Brokers" entry
- [ ] 1.2 In the `useEffect` URL param handler, map both `?tab=portfolios` and `?tab=integrations` to activate the `portfolios-brokers` tab (backward compat)
- [ ] 1.3 Render `<PortfoliosBrokersHub />` in the tab body when `activeTab === "portfolios-brokers"`

## 2. Hub Accordion Component

- [ ] 2.1 Create `frontend/components/settings/PortfoliosBrokersHub.tsx` with `useState<Set<string>>` for `expandedPortfolioIds` (decoupled from query state)
- [ ] 2.2 Render each portfolio as an accordion row: color swatch, name, base currency, default-star button, Edit button, and expand/collapse chevron
- [ ] 2.3 On expand, render the child accounts section with a list of `AccountRow` sub-components and an "Add Broker Account" CTA button
- [ ] 2.4 Auto-expand the single portfolio if there is exactly one on initial load; otherwise default all collapsed
- [ ] 2.5 Render account rows with name, broker type badge (IBKR / SCHWAB / MANUAL), and status badge (Connected / Error / Inactive) derived from `is_active` and last sync status
- [ ] 2.6 Each account row has an Edit button that opens the `BrokerAccountEditModal` pre-filled with that account's data
- [ ] 2.7 Render a "Create New Portfolio" button at the top of the hub that opens `PortfolioCreateModal`

## 3. Portfolio Create Modal

- [ ] 3.1 Create `frontend/components/settings/modals/PortfolioCreateModal.tsx` as a fixed-overlay modal dialog
- [ ] 3.2 Add fields: Portfolio Name (text input, required), Base Currency (select, CURRENCY_ALLOWLIST, default USD), Color (PORTFOLIO_COLORS chip picker)
- [ ] 3.3 Add a prominent notice block: "The base currency cannot be changed after the portfolio is created. It serves as the foundation for all performance metrics."
- [ ] 3.4 On submit, call `POST /api/v1/portfolios`; on success invalidate `["portfolios"]` query and close modal; on error show inline error
- [ ] 3.5 Validate that name is non-empty before enabling the submit button

## 4. Portfolio Edit Modal

- [ ] 4.1 Create `frontend/components/settings/modals/PortfolioEditModal.tsx` as a fixed-overlay modal dialog
- [ ] 4.2 Add editable fields: Portfolio Name (text input, pre-filled) and Color (chip picker, pre-selected)
- [ ] 4.3 Render base currency as a read-only text badge (not a select)
- [ ] 4.4 On submit, call `PATCH /api/v1/portfolios/{id}`; on success invalidate `["portfolios"]` query and close modal
- [ ] 4.5 Add a "Danger Zone" section styled with red border/background containing: warning text about cascading delete, a text input where user must type the exact portfolio name, and a "Delete Portfolio" button
- [ ] 4.6 Keep the Delete Portfolio button disabled until `confirmInput === portfolio.name` (case-sensitive exact match)
- [ ] 4.7 On delete confirmed, call `DELETE /api/v1/portfolios/{id}`; on success invalidate `["portfolios"]` and close modal

## 5. Broker Account Create Modal

- [ ] 5.1 Create `frontend/components/settings/modals/BrokerAccountCreateModal.tsx` accepting `portfolioId` and `portfolioName` as required props
- [ ] 5.2 Display "Target Portfolio: [portfolioName]" as read-only text at the top of the modal
- [ ] 5.3 Add fields: Display Name (text input, required), Broker Type (select: IBKR / SCHWAB / MANUAL)
- [ ] 5.4 Dynamically show credential fields based on selected broker type using `CREDENTIAL_FIELDS` map from `AccountForm.tsx`; hide credential section for `manual` type
- [ ] 5.5 Add Import Settings section with a date input for sync start date, defaulting to `${currentYear}-01-01`
- [ ] 5.6 Add "Test Connection" button that calls `POST /api/v1/accounts/test-connection`; show inline green/red result; keep Save button enabled regardless of result; show spinner while pending
- [ ] 5.7 On submit, call `POST /api/v1/portfolios/{portfolioId}/accounts`; on success invalidate `["accounts", portfolioId]` and `["portfolios"]`; close modal
- [ ] 5.8 Validate display name non-empty before enabling submit button

## 6. Broker Account Edit Modal

- [ ] 6.1 Create `frontend/components/settings/modals/BrokerAccountEditModal.tsx` accepting the full account object as a prop
- [ ] 6.2 Render Display Name as an editable text input (pre-filled)
- [ ] 6.3 Render broker type as a static read-only badge (span/div, not a select)
- [ ] 6.4 Render credential fields as `type="password"` inputs with empty initial value; add hint text "Leave blank to keep existing credentials" below each field
- [ ] 6.5 Include the same "Test Connection" button (non-blocking) as in the create modal
- [ ] 6.6 Add a Status section: if `account.is_active` is true, show "Deactivate Account" button; if false, show "Reactivate Account" button
- [ ] 6.7 Deactivate/Reactivate calls `PATCH /api/v1/portfolios/{portfolioId}/accounts/{id}` with `{ is_active: false/true }`; on success invalidate accounts query
- [ ] 6.8 On main Save, submit only name and any non-empty credential values; call `PATCH /api/v1/portfolios/{portfolioId}/accounts/{id}`; on success close modal
- [ ] 6.9 Ensure there is NO delete button in this modal

## 7. Wiring & Cleanup

- [ ] 7.1 Export all new modal components from a `frontend/components/settings/modals/index.ts` barrel file
- [ ] 7.2 Remove (or mark deprecated) the old `AccountSettings.tsx` tab rendering path from `SettingsPageClient`; keep the component file until the new hub is verified in tests
- [ ] 7.3 Verify that the existing `PortfolioSettings.tsx` is no longer imported in `SettingsPageClient` after the hub replaces it; update imports accordingly

## 8. Tests

- [ ] 8.1 Write unit tests for `PortfoliosBrokersHub`: accordion expand/collapse, auto-expand for single portfolio, no collapse on refetch
- [ ] 8.2 Write unit tests for `PortfolioCreateModal`: validation, currency warning, chip picker, submit calls correct API
- [ ] 8.3 Write unit tests for `PortfolioEditModal`: base currency read-only, Danger Zone type-to-confirm pattern, delete disabled until name matches
- [ ] 8.4 Write unit tests for `BrokerAccountCreateModal`: portfolio context injection, dynamic credential fields, test connection non-blocking behavior
- [ ] 8.5 Write unit tests for `BrokerAccountEditModal`: masked credentials, immutable type badge, deactivate/reactivate toggle, no delete button present
