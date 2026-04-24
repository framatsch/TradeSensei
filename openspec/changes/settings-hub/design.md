## Context

The current Settings page (`/dashboard/settings`) has four tabs (General, Accounts & Integrations,
Corporate Actions, Features) built on a simple string-typed enum and a flat `user_settings`
key-value table. Spec 1 introduced the `Portfolio` entity and its API; Spec 2 introduced the
`TopBar` with a UserBadge → Settings link and a global `activePortfolioId` Zustand store. Spec 3
uses all of this infrastructure to become the full administrative hub.

**Current state of each asset this spec touches:**

| Asset | State |
|---|---|
| Settings tab component | 4 tabs, `Tab` type union, `TABS` array |
| Playbook/Tag pages | Standalone sidebar pages at `/dashboard/playbooks` and `/dashboard/tags` |
| `user_settings` table | Key-value; keys `theme`, `default_date_range`, `features` (serialised JSON) |
| Portfolio API | Fully implemented (Spec 1); `GET/POST/PATCH/DELETE /api/v1/portfolios` |
| `activePortfolioId` Zustand | Implemented (Spec 2) |
| Fresh Start | Exists at account level: `POST /api/v1/imports/{account_id}/fresh-start` |

## Goals / Non-Goals

**Goals:**

- Consolidate all configuration into Settings; make the sidebar operational-only.
- Add Portfolios tab: CRUD UI for portfolios scoped to the authenticated user; Danger Zone with
  per-account fresh start on all accounts.
- Add Playbooks & Tags tab: relocate existing components without rewriting them.
- Add Look & Feel tab: store `chart_candles_before` (int, default 20),
  `chart_candles_after` (int, default 10), `chart_show_post_exit` (bool, default false) in
  `user_settings`; expose them in `UserSettingsRead` / `UserSettingsUpdate`.
- Scope the Accounts & Integrations tab to `activePortfolioId`.
- Remove `/dashboard/playbooks` and `/dashboard/tags` routes (redirect to
  `/dashboard/settings?tab=playbooks-tags`).

**Non-Goals:**

- Per-playbook candle defaults (deferred to Spec 6).
- Portfolio-level fresh start endpoint (account-level is sufficient; Danger Zone wipes each
  account in the portfolio sequentially using the existing endpoint).
- Candle Style or Feature Toggle controls in Look & Feel (candle style is a chart-level concern;
  feature flags already have their own tab).
- Live account sync / broker API connections (Iteration 8 stretch).
- Multi-currency P&L conversion UI.

## Decisions

### D1 — Chart defaults stored in `user_settings`, not a new table

**Decision:** Add `chart_candles_before`, `chart_candles_after`, `chart_show_post_exit` as new
recognised keys in the existing `user_settings` key-value table. Extend `UserSettingsRead` and
`UserSettingsUpdate` Pydantic schemas to include these typed fields alongside `theme`,
`default_date_range`, and `features`.

**Alternatives considered:**
- New `user_preferences` typed table — overkill for three scalar values; requires a migration,
  new model, new repository, new service, and new endpoint.
- JSONB column on `users` table — tight coupling; harder to add/remove keys without migration.
- New settings key `"chart_display"` storing a JSON blob — less discoverable, breaks the existing
  flat schema contract, requires custom serialisation.

**Chosen because:** Zero migration cost; consistent with the existing pattern; three named fields
in the Pydantic schema are fully typed and self-documenting. The service layer already knows how
to read all recognised keys into a single `UserSettingsRead` object.

### D2 — `base_currency` immutable once any trade exists

**Decision:** The Portfolios tab disables the `base_currency` input and shows a tooltip once
`has_trades` is true. The backend already enforces this in `update_portfolio` (Spec 1). The UI
matches the backend constraint without adding a separate client-side guard.

**Alternatives:** Always editable with a warning (rejected — silent P&L inconsistency).
Unlockable after deleting all trades (rejected — increases UI complexity for a rare edge case).

### D3 — Playbook/Tag pages become redirects, not removed outright

**Decision:** `/dashboard/playbooks/page.tsx` and `/dashboard/tags/page.tsx` are replaced with
`redirect('/dashboard/settings?tab=playbooks-tags')` instead of being deleted. This preserves
any bookmarks or direct links without a 404.

**Why not delete:** Any external link (user bookmark, notification deep-link) would break with a
404. A permanent redirect is low-cost and safe.

### D4 — Danger Zone uses existing account-level fresh start

**Decision:** The Portfolios tab Danger Zone iterates over all accounts belonging to a portfolio
and calls `POST /api/v1/imports/{account_id}/fresh-start` for each, client-side, with a
sequential `Promise` chain (not a new endpoint). A confirmation dialog requires the user to type
the portfolio name before proceeding.

**Why not a portfolio-level endpoint:** Adding a new endpoint adds backend scope without clear
benefit at this stage. The client-side loop handles the same semantics; if any account fails the
UI shows a partial-failure state.

**Risk:** If the user navigates away mid-wipe the operation is partially applied. This is
acceptable at current scale (portfolios have few accounts); a server-side batch endpoint can be
added when needed.

### D5 — Accounts & Integrations tab scoped to `activePortfolioId`

**Decision:** `AccountSettings` component reads `activePortfolioId` from `useActivePortfolio()`
(Spec 2) and passes it to `useAccounts(portfolioId)`. If Spec 2 is not yet applied, the tab
falls back gracefully by showing all accounts (the hook's `portfolioId` param is optional).

### D6 — Tab union type extended, not replaced

**Decision:** `Tab` type in `SettingsPageClient.tsx` is extended from a 4-value to a 7-value
union. The `TABS` constant array gains three entries. URL deep-linking via `?tab=` is extended to
handle the three new ids (`portfolios`, `playbooks-tags`, `look-and-feel`).

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| Spec 1 / Spec 2 not merged when Spec 3 lands | Portfolio tab calls `usePortfolios()` — if the hook returns empty/error it shows a "prerequisite not available" banner instead of crashing. |
| Partial portfolio wipe (user navigates away) | Confirmation dialog requires portfolio name; success/error toast shown per account; UI state reflects which accounts were wiped. |
| `chart_candles_before` / `chart_candles_after` used before Spec 6 | Keys are ignored by the Journal until Spec 6. Safe to write early — reads that encounter missing keys fall back to defaults. |
| Sidebar items removed before user learns about Settings | `EmptyPortfolioGate` CTA (Spec 2) already links to `/dashboard/settings?tab=portfolios`. Redirect from old routes handles muscle-memory navigation. |

## Migration Plan

1. **Backend** (no migration): Add three fields to `UserSettingsRead` / `UserSettingsUpdate`
   schemas with typed defaults. Update `users.py` route handler to read/write the new keys.
2. **Frontend** (Settings page): Extend `SettingsPageClient`, add three new component files,
   update `AccountSettings` to accept `portfolioId`.
3. **Sidebar**: Remove `playbooks` and `tags` nav links.
4. **Route redirects**: Replace page bodies of `/dashboard/playbooks` and `/dashboard/tags`.
5. **Rollback**: Revert the four files changed in steps 2–4; the backend schema addition is
   additive and harmless if left in place (ignored by the frontend).

## Open Questions

- None — resolved by user decisions before proposal was written.
