## Why

The application currently has a growing list of optional and experimental features (e.g. MAE/MFE metrics, live broker connections, rolling win-rate chart) but no unified way to control their visibility. Adding a feature flag system backed by user-level settings allows individual capabilities to be toggled per user without code deployments, and provides a clear extension point for future opt-in features.

## What Changes

- Add a new `features` settings key to the existing `user_settings` key-value store, storing a JSON object of boolean flags per user
- Extend the `UserSettingsRead` and `UserSettingsUpdate` Pydantic schemas to include a `features` field
- Add a `useFeatureFlag(key)` React hook that reads flags from the settings cache — no extra network request
- Add a **Features** section to the Settings page (General tab) where users can toggle each flag on/off
- Gate at least two existing capabilities behind flags as the initial integration: `rolling_winrate_chart` and `mae_mfe` (the latter is a new placeholder for future MAE/MFE work)

## Capabilities

### New Capabilities
- `feature-flags-settings`: Backend — extend `user_settings` to store a `features` JSON blob; update schema + service + repository to read/write it
- `feature-flags-ui`: Frontend — `useFeatureFlag` hook, `FeaturesSettings` component, integrate flags into sidebar nav and existing chart renders

### Modified Capabilities
- `user-settings`: The `UserSettingsRead` and `UserSettingsUpdate` schemas gain a new optional `features` field; the service layer must merge flag updates rather than overwriting the whole object

## Impact

- **Backend**: `app/schemas/user.py`, `app/services/user_service.py`, `app/repositories/user_repository.py` — add `features` field handling; no new migration needed (stored as JSON text in the existing `user_settings` key-value table under the key `"features"`)
- **Frontend**: new `useFeatureFlag.ts` hook, new `FeaturesSettings.tsx` component, `GeneralSettings.tsx` extended or a new tab added, `useSettings.ts` + `lib/types.ts` updated
- **Sidebar nav**: `rolling-winrate-chart` nav item conditionally hidden/shown by flag
- **No breaking changes**: All flags default to `false` (opt-in); all existing API consumers continue working unchanged
