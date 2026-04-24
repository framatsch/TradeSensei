## Why

The app currently has no single place to configure its global resources. Portfolios (introduced in
Spec 1), playbooks, tags, and chart display preferences are scattered across sidebar pages and a
settings tab that only covers theme and date-range. Spec 3 consolidates all configuration into a
unified **Settings Hub** — the administrative "hangar" that is strictly separated from the
operational "cockpit" (dashboard, journal, analytics).

## What Changes

- **NEW** `portfolios` tab in Settings — full CRUD for the Portfolio entity introduced by Spec 1
  (name, color, currency, live/paper type); includes a **Danger Zone** with per-portfolio wipe.
- **NEW** `playbooks-tags` tab in Settings — moves Playbook and Tag management out of the sidebar
  into the Hub; standalone `/dashboard/playbooks` and `/dashboard/tags` pages are removed.
- **NEW** `look-and-feel` tab in Settings — stores chart display defaults:
  `candles_before_entry` (int), `candles_after_exit` (int), `show_post_exit_candles` (bool).
  These are global user defaults; the Journal (Spec 6) reads them and allows per-trade overrides.
- **MODIFIED** Settings page tab list gains three new tabs (`portfolios`, `playbooks-tags`,
  `look-and-feel`) and loses the route dependency on standalone playbook/tag pages.
- **MODIFIED** `user_settings` key-value store gains three new recognised keys:
  `chart_candles_before`, `chart_candles_after`, `chart_show_post_exit`.
- **REMOVED** Standalone sidebar routes `/dashboard/playbooks` and `/dashboard/tags` (redirects
  to `/dashboard/settings?tab=playbooks-tags` installed to preserve any bookmarks).

## Capabilities

### New Capabilities

- `portfolio-settings`: CRUD UI for portfolios in Settings; reads from the portfolio API
  introduced in Spec 1; enforces currency-immutability UX (field disabled once trades exist);
  includes Danger Zone with per-portfolio wipe (uses existing
  `POST /imports/{account_id}/fresh-start` on all accounts of the portfolio).
- `playbooks-tags-settings`: Settings tab that hosts the existing `PlaybookList` and `TagList`
  components under a single tab; replaces the standalone sidebar pages.
- `chart-display-settings`: Settings tab that reads/writes three new keys in `user_settings`
  (`chart_candles_before`, `chart_candles_after`, `chart_show_post_exit`); backend adds these
  keys to the `UserSettingsRead` / `UserSettingsUpdate` Pydantic schemas and the service that
  serialises them; default values baked into the schema (`20`, `10`, `false`).

### Modified Capabilities

- `account-management`: The existing Accounts & Integrations tab is now scoped to the
  **active portfolio** (reads `activePortfolioId` from the Zustand store introduced in Spec 2
  instead of showing all user accounts).

## Impact

- **Backend**: `UserSettingsRead` and `UserSettingsUpdate` gain three new optional fields;
  `UserSettingsService` (or equivalent handler in `users.py`) must read/write these three keys
  from `user_settings`; no new table or migration required.
- **Frontend**: `SettingsPageClient` gains three new tabs; new components
  `PortfolioSettings`, `PlaybooksTagsSettings`, `ChartDisplaySettings`; `AccountSettings`
  updated to filter by `activePortfolioId`; sidebar nav loses `playbooks` and `tags` entries;
  `/dashboard/playbooks` and `/dashboard/tags` become redirect pages.
- **No new DB migration**: chart defaults piggyback on the existing `user_settings` key-value
  table; no schema changes.
- **Dependency**: Spec 1 (`portfolio-core-data-model`) must be applied before the Portfolios tab
  can call the portfolio API. Spec 2 (`app-state-topbar-navigation`) must be applied before
  `AccountSettings` can consume `activePortfolioId` and before the UserBadge → Settings link
  works.
