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

### D3 — Playbook/Tag pages redirect to Library context, not Settings

**Decision:** `/dashboard/playbooks/page.tsx` and `/dashboard/tags/page.tsx` are replaced with
`redirect('/dashboard/library/playbooks')` and `redirect('/dashboard/library/tags')` respectively
(handled in Spec 2 tasks). Playbooks and Tags are **not** a Settings tab — they are managed in
the Global Library application context introduced by Spec 2.

**Why not Settings:** Spec 2 establishes the Global Library as a first-class application context
(accessible via BentoMenu). Putting Playbooks/Tags in Settings would contradict that architecture
and force users to leave the operational flow to manage strategic entities.

**Implication for this spec:** `SettingsPageClient` does NOT gain a `playbooks-tags` tab. The
`PlaybooksTagsSettings` component is not created. Tab count remains at 6 (General, Integrations,
Corporate Actions, Features, Portfolios, Look & Feel).

### D4 — Portfolio colour uses chip picker (same pattern as Tag colours)

**Decision:** The portfolio `color_hex` field in the create/edit form is presented as a row of
colour chip buttons (small filled circles), identical in interaction to the Tag colour picker
already in the codebase. The user clicks a chip to select the colour; the chip becomes visually
active (ring/border). No free-form hex input is shown to the user.

**Colour set:** A fixed palette of 12 colours is defined in a shared constant
`PORTFOLIO_COLORS: string[]`. The migration default `'#6366f1'` (indigo) is included.

**Why chip picker, not free-form hex:** Consistency with Tags; colour validation is trivially
satisfied server-side because only palette values can be submitted; no `^#[0-9A-Fa-f]{6}$`
regex validation needed on the frontend.

---

### D5 — Default portfolio stored in `user_settings`, not on the Portfolio model

**Decision:** The concept of "default portfolio" (the one auto-selected when entering Portfolio
Workspace via BentoMenu if no prior selection is stored) is stored as a new key
`"default_portfolio_id"` (UUID string) in the existing `user_settings` key-value table. The
`Portfolio` model itself gains no `is_default` column.

**Alternatives considered:**
- *`is_default` boolean on Portfolio model* — requires a migration; enforcing single-default
  across rows needs a DB-level constraint or application guard; also leaks UI preference into
  the data model. Rejected.
- *Infer from `created_at` order* — already the fallback in Spec 2's stale-ID recovery. The
  user-configured default overrides this fallback.

**UX in Settings:** Each portfolio card in the Portfolios tab has a "Set as default" action
(star icon or radio button). The currently configured default is visually indicated. Setting a
new default updates `user_settings.default_portfolio_id` via `PUT /api/v1/users/me/settings`.

**Stale reference guard:** If `default_portfolio_id` points to a portfolio that no longer exists,
`useActivePortfolio` ignores the stored value and falls back to `portfolios[0].id` (as per Spec
2 D10).

---

### D6 — Danger Zone uses existing account-level fresh start

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

### D7 — Tab union type extended, not replaced

**Decision:** `Tab` type in `SettingsPageClient.tsx` is extended from a 4-value to a 6-value
union (adding `portfolios` and `look-and-feel`; NOT adding `playbooks-tags`). The `TABS`
constant array gains two entries. URL deep-linking via `?tab=` handles the two new ids.

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| Spec 1 / Spec 2 not merged when Spec 3 lands | Portfolio tab calls `usePortfolios()` — if the hook returns empty/error it shows a "prerequisite not available" banner instead of crashing. |
| Partial portfolio wipe (user navigates away) | Confirmation dialog requires portfolio name; success/error toast shown per account; UI state reflects which accounts were wiped. |
| `chart_candles_before` / `chart_candles_after` used before Spec 6 | Keys are ignored by the Journal until Spec 6. Safe to write early — reads that encounter missing keys fall back to defaults. |
| `default_portfolio_id` points to deleted portfolio | `useActivePortfolio` (Spec 2) ignores stale value and falls back to `portfolios[0].id`. No crash. |
| Colour palette insufficient for users with many portfolios | Fixed palette of 12 colours allows repetition; visual differentiation relies on name + colour combined. Acceptable for MVP. |

## Migration Plan

1. **Backend** (no migration): Add four fields to `UserSettingsRead` / `UserSettingsUpdate`
   schemas (`chart_candles_before`, `chart_candles_after`, `chart_show_post_exit`,
   `default_portfolio_id`) with typed defaults. Update `users.py` route handler to read/write
   the new keys.
2. **Frontend** (Settings page): Extend `SettingsPageClient` with 2 new tabs; add component
   files `PortfolioSettings.tsx` and `ChartDisplaySettings.tsx`; update `AccountSettings` to
   accept `portfolioId`. Do NOT add `PlaybooksTagsSettings.tsx`.
3. **Route redirects**: `/dashboard/playbooks` → `/dashboard/library/playbooks`;
   `/dashboard/tags` → `/dashboard/library/tags` (handled by Spec 2 task 7.5/7.6).
4. **Rollback**: Revert the component files changed in step 2; the backend schema additions are
   additive and harmless if left in place.

## Open Questions

- None — resolved by user decisions before proposal was written.
