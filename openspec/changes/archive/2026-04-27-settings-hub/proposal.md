> **Execution order: Spec 3 of 3**
> Depends on: **Spec 1 (`portfolio-core-data-model`) AND Spec 2 (`app-state-topbar-navigation`) must both be merged.**
> See `openspec/changes/PORTFOLIO-EXECUTION-ORDER.md` for the full chain.

---

## Why

The app currently has no single place to configure its global resources. Portfolios (introduced in
Spec 1), playbooks, tags, and chart display preferences are scattered across sidebar pages and a
settings tab that only covers theme and date-range. Spec 3 consolidates all configuration into a
unified **Settings Hub** — the administrative "hangar" that is strictly separated from the
operational "cockpit" (dashboard, journal, analytics).

## What Changes

- **NEW** `portfolios` tab in Settings — full CRUD for the Portfolio entity introduced by Spec 1
  (name, colour chip picker, currency, **default portfolio toggle**); includes a
  **Danger Zone** with per-portfolio wipe.
- **NEW** `look-and-feel` tab in Settings — stores chart display defaults:
  `candles_before_entry` (int), `candles_after_exit` (int), `show_post_exit_candles` (bool).
  These are global user defaults; the Journal (Spec 6) reads them and allows per-trade overrides.
- **MODIFIED** Settings page tab list gains two new tabs (`portfolios`, `look-and-feel`).
  The `playbooks-tags` tab is **not added** — Playbooks and Tags are now managed in the Global
  Library context (Spec 2).
- **MODIFIED** `user_settings` key-value store gains four new recognised keys:
  `chart_candles_before`, `chart_candles_after`, `chart_show_post_exit`,
  `default_portfolio_id`.

## Capabilities

### New Capabilities

- `portfolio-settings`: CRUD UI for portfolios in Settings; reads from the portfolio API
  introduced in Spec 1; colour chip picker (same pattern as Tag colour chips) for `color_hex`;
  enforces currency-immutability UX (field disabled once trades exist); **default portfolio
  selector** (radio or star toggle) — marks one portfolio as the default; its ID is stored in
  `user_settings` under key `default_portfolio_id`; includes Danger Zone with per-portfolio wipe
  (uses existing `POST /imports/{account_id}/fresh-start` on all accounts of the portfolio).
- `chart-display-settings`: Settings tab that reads/writes three new keys in `user_settings`
  (`chart_candles_before`, `chart_candles_after`, `chart_show_post_exit`); backend adds these
  keys to the `UserSettingsRead` / `UserSettingsUpdate` Pydantic schemas and the service that
  serialises them; default values baked into the schema (`20`, `10`, `false`).

### Modified Capabilities

- `account-management`: The existing Accounts & Integrations tab is now scoped to the
  **active portfolio** (reads `activePortfolioId` from the Zustand store introduced in Spec 2
  instead of showing all user accounts).

## Impact

- **Backend**: `UserSettingsRead` and `UserSettingsUpdate` gain four new optional fields
  (`chart_candles_before`, `chart_candles_after`, `chart_show_post_exit`,
  `default_portfolio_id`); no new table or migration required.
- **Frontend**: `SettingsPageClient` gains two new tabs (`portfolios`, `look-and-feel`);
  new components `PortfolioSettings`, `ChartDisplaySettings`; `AccountSettings` updated to
  filter by `activePortfolioId`; **no** `PlaybooksTagsSettings` component (Playbooks/Tags are
  in the Library context from Spec 2); `/dashboard/playbooks` and `/dashboard/tags` redirect
  to `/dashboard/library/playbooks` and `/dashboard/library/tags` respectively (handled by
  Spec 2 tasks).
- **No new DB migration**: chart defaults and default_portfolio_id piggyback on the existing
  `user_settings` key-value table.
- **Dependency**: Spec 1 (`portfolio-core-data-model`) must be applied before the Portfolios tab
  can call the portfolio API. Spec 2 (`app-state-topbar-navigation`) must be applied before
  `AccountSettings` can consume `activePortfolioId` and before the UserBadge → Settings link
  works.
