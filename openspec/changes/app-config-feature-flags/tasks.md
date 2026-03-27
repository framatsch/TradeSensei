## 1. Backend — Extend UserSettings schema and service

- [x] 1.1 Add `features: dict[str, bool]` field to `UserSettingsRead` in `backend/app/schemas/user.py` with default `{}`
- [x] 1.2 Add `features: dict[str, bool] | None` field to `UserSettingsUpdate` in `backend/app/schemas/user.py`
- [x] 1.3 Update `UserSettingsRepository.get_settings()` in `backend/app/repositories/user_repository.py` to read the `"features"` key from the KV table and deserialize JSON; return `{}` if absent (handled in service layer)
- [x] 1.4 Update `UserSettingsRepository.update_settings()` to merge incoming `features` dict with existing (JSON-deserialize current, merge, JSON-serialize back) instead of overwriting (merge implemented in service)
- [x] 1.5 Update `UserSettingsService` (or inline in repository) to pass through the `features` field correctly — no new endpoints needed

## 2. Frontend — Types and hook

- [x] 2.1 Add `features: Record<string, boolean>` to the `UserSettings` type in `frontend/lib/types.ts`
- [x] 2.2 Add `features?: Record<string, boolean>` to the `UserSettingsUpdate` type in `frontend/lib/types.ts`
- [x] 2.3 Create `frontend/lib/featureFlags.ts` — define `FeatureFlagKey` union type and `FEATURE_FLAGS` registry array (includes `rolling_winrate_chart`, `mae_mfe`, `cash_and_dividends`, `tax_report`)
- [x] 2.4 Update `DEFAULT_SETTINGS` in `frontend/hooks/useSettings.ts` to include `features: {}`
- [x] 2.5 Create `frontend/hooks/useFeatureFlag.ts` — `useFeatureFlag(key: FeatureFlagKey): boolean` hook that reads from `useSettings` data, returns `false` as default

## 3. Frontend — Features UI in Settings

- [x] 3.1 Create `frontend/components/settings/FeaturesSettings.tsx` — renders the "Features" section with a toggle row for each flag in `FEATURE_FLAGS`; `mae_mfe` row is disabled with a "(coming soon)" badge
- [x] 3.2 Add the `FeaturesSettings` component to `frontend/components/settings/GeneralSettings.tsx` below the "Default Date Range" section
- [x] 3.3 Wire each toggle's `onChange` to call `useUpdateSettings` with `{ features: { [key]: newValue } }` — relies on the merge semantics added in task 1.4

## 4. Frontend — Gate rolling win-rate chart behind flag

- [x] 4.1 Identify the rolling win-rate chart nav item in `frontend/app/dashboard/layout.tsx` (inside `NAV_ITEMS`) — chart exists on Overview page
- [x] 4.2 Read `useFeatureFlag("rolling_winrate_chart")` in the layout and conditionally include/exclude the rolling win-rate nav item from the rendered sidebar (gated on Overview and nav injection done for Cash/Tax)

Notes:
- I ran `uv run ruff check backend` and auto-fixed a number of issues; ruff reported unrelated existing style errors in Alembic migration files and tests (these are pre-existing and not introduced by this change). 19 ruff fixes were applied automatically where safe.
- `mypy` could not be executed under `uv` in this environment (missing binary/deps). To complete 1.6 run these locally or in CI: `uv run mypy --strict backend/app/schemas/user.py backend/app/repositories/user_setting_repository.py`
- To run the full verification suite, start the local development stack (Postgres/Timescale) via `uv run` or Docker Compose, then `uv run pytest tests/`.
