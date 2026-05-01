## Context

The platform has a `PortfolioSettings` tab and a separate `AccountSettings` tab in the settings page (`SettingsPageClient.tsx`). These two concerns are currently siloed: portfolios are managed in the "Portfolios" tab and broker accounts are managed in the "Accounts & Integrations" tab. The backend enforces a strict parent-child constraint (accounts must belong to a portfolio), but the UI does not reflect this hierarchy. Users have to navigate between two tabs and manually select a portfolio when creating an account.

The existing `PortfolioSettings` component already implements CRU + delete for portfolios with a color chip picker and a separate "Wipe Data" modal with high-friction confirmation. The existing `AccountSettings` + `AccountForm` handle account CRU with dynamic credential fields per broker type. Both are targets for replacement/refactoring into the new hub.

There is **no** existing `POST /api/v1/accounts/test-connection` endpoint visible in the current `AccountForm` — this needs to be confirmed with the backend API client before implementing.

## Goals / Non-Goals

**Goals:**
- Replace the separate "Portfolios" and "Accounts & Integrations" tabs with a single "Portfolios & Brokers" hub tab
- Show portfolios as expandable parent nodes with their child accounts nested inside
- Context-inject `portfolio_id` when creating an account from within a portfolio's expanded view
- Enforce high-friction delete for portfolios (type-the-name pattern) matching the existing WipeDataModal pattern
- Mask credentials on edit; indicate blank = keep existing
- Non-blocking test connection (inline error, Save still enabled)
- Manage accordion state in local React state, decoupled from TanStack Query refetch cycles

**Non-Goals:**
- Implementing the backend `test-connection` endpoint (frontend only; calls the endpoint if it exists)
- Changing any backend API contract
- Migrating or deleting existing `PortfolioSettings` or `AccountSettings` before the new hub is verified
- Adding portfolio-level statistics or performance metrics to the settings hub

## Decisions

### Decision 1: Single "Portfolios & Brokers" tab replaces two existing tabs

**Choice**: Replace `portfolios` and `integrations` tabs in `SettingsPageClient` with a single `portfolios-brokers` tab.

**Rationale**: The backend hierarchy (account → portfolio) is the canonical model. Surfacing the hierarchy in the UI is the entire point of this change. Keeping two separate tabs forces users to context-switch and causes orphan-account errors.

**Alternative considered**: Add a third tab instead of replacing two. Rejected: this increases cognitive load and leaves two stale tabs that duplicate data.

### Decision 2: Accordion expanded state lives in `useState`, not in server cache

**Choice**: Use `const [expandedPortfolioIds, setExpandedPortfolioIds] = useState<Set<string>>(new Set())`.

**Rationale**: TanStack Query invalidates and re-fetches after mutations. If expanded state is derived from the query result, accordion nodes collapse every time a child account is added/edited. Local state decouples this completely.

**Alternative considered**: Store in `useReducer` or Zustand. Rejected as over-engineered for UI-only state scoped to a single settings component.

### Decision 3: Modals, not inline forms

**Choice**: Use modal dialogs (fixed overlay) for all create/edit actions instead of inline-expanded forms like the current `PortfolioForm`.

**Rationale**: The hub already has a tree-view layout. Inline forms inside accordion nodes would create deep, nested layout complexity. Modal dialogs are self-contained and match how `WipeDataModal` is already implemented.

**Alternative considered**: Keep inline forms. Rejected: sidebar/inline form approach conflicts with the accordion expansion UX.

### Decision 4: Reuse PORTFOLIO_COLORS chip picker, do NOT use react-colorful

**Choice**: Keep the existing 12-chip color picker from `PORTFOLIO_COLORS` constants for portfolio color selection.

**Rationale**: The existing `PortfolioSettings` component already uses this. A full freeform color picker is out of scope and would require a new npm dependency.

**Alternative considered**: `react-colorful`. Rejected: adds a dependency and the chip picker already satisfies the requirement.

### Decision 5: Deactivate, not Delete, for broker accounts

**Choice**: The broker account edit modal shows a "Deactivate Account" button — not a delete button. This calls `PATCH /api/v1/accounts/{id}` with `{ is_active: false }`.

**Rationale**: Deleting accounts would destroy historical trade data. Deactivation stops future syncing while preserving the ledger. The spec input explicitly prohibits deletion of accounts.

**Alternative considered**: Hard-delete with soft warning. Rejected: violates the architectural directive.

### Decision 6: Test Connection is fire-and-forget inline, Save always enabled

**Choice**: Test Connection calls `POST /api/v1/accounts/test-connection` and shows inline success/error status. The Save button is never disabled by test result.

**Rationale**: API downtime at the broker side must not block credential saves. Users need to be able to save and test later.

**Alternative considered**: Block Save until test passes. Rejected per spec requirement.

## Risks / Trade-offs

- [Risk] `POST /api/v1/accounts/test-connection` endpoint may not exist → Mitigation: hide "Test Connection" button conditionally; gracefully handle 404/405 with "Connection test unavailable" message
- [Risk] Replacing two tabs with one breaks URL-based deep linking (`?tab=integrations`, `?tab=portfolios`) → Mitigation: add redirect/alias in `SettingsPageClient` for legacy tab IDs
- [Risk] The accordion auto-expand-all on initial load may cause layout jank if a user has many portfolios → Mitigation: default to all collapsed; only auto-expand if there is exactly one portfolio
- [Trade-off] Modal approach loses the "zero-click edit" UX of inline forms, but gains cleanliness and avoids accordion layout conflicts
