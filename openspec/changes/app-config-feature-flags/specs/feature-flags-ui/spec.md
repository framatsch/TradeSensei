## ADDED Requirements

### Requirement: Known feature flags registry
The frontend SHALL define a single source-of-truth registry of all known feature flags in `frontend/lib/featureFlags.ts`. Each entry SHALL have a `key` (string, snake_case), a `label` (human-readable name), and a `description` (one sentence explaining the feature). Initial flags: `rolling_winrate_chart` and `mae_mfe`.

#### Scenario: Registry is importable
- **WHEN** a component imports `FEATURE_FLAGS` from `lib/featureFlags`
- **THEN** it receives a typed array of `{key, label, description}` objects with at least two entries

### Requirement: useFeatureFlag hook
The frontend SHALL provide a `useFeatureFlag(key: FeatureFlagKey)` hook in `frontend/hooks/useFeatureFlag.ts`. The hook SHALL read from the TanStack Query settings cache (via `useSettings`) and return a boolean. It SHALL return `false` when the settings have not yet loaded or when the key is absent from the features map.

#### Scenario: Flag is enabled
- **WHEN** the settings cache contains `features: { rolling_winrate_chart: true }`
- **AND** a component calls `useFeatureFlag("rolling_winrate_chart")`
- **THEN** the hook returns `true`

#### Scenario: Flag is absent (new user, no features key)
- **WHEN** the settings cache contains `features: {}` or `features` is not yet loaded
- **AND** a component calls `useFeatureFlag("rolling_winrate_chart")`
- **THEN** the hook returns `false`

#### Scenario: Unknown key returns false
- **WHEN** a component calls `useFeatureFlag` with a key not in the registry
- **THEN** TypeScript raises a compile-time type error (the key type is a union of known keys)

### Requirement: Features section in General Settings
The General Settings tab SHALL render a "Features" section below the existing "Default Date Range" section. It SHALL list all known flags from the registry, each as a toggle row showing the label, description, and an on/off switch. Toggling a switch SHALL call `useUpdateSettings` with `{ features: { [key]: newValue } }`.

#### Scenario: Flags section renders
- **WHEN** the user opens Settings → General
- **THEN** a "Features" heading and at least the `rolling_winrate_chart` and `mae_mfe` toggle rows are visible

#### Scenario: Toggle enables a flag
- **WHEN** the user clicks the toggle for "Rolling Win-Rate Chart" (currently off)
- **THEN** `PUT /api/v1/users/me/settings` is called with `{ "features": { "rolling_winrate_chart": true } }`
- **AND** the toggle immediately reflects the enabled state (optimistic update)

#### Scenario: Toggle disables a flag
- **WHEN** the user clicks the toggle for "Rolling Win-Rate Chart" (currently on)
- **THEN** `PUT /api/v1/users/me/settings` is called with `{ "features": { "rolling_winrate_chart": false } }`
- **AND** the toggle immediately reflects the disabled state

### Requirement: Rolling win-rate chart gated by feature flag
The sidebar navigation entry for the rolling win-rate chart SHALL only be visible when the `rolling_winrate_chart` feature flag is `true` for the current user.

#### Scenario: Flag disabled — link hidden
- **WHEN** `rolling_winrate_chart` flag is `false` (or absent)
- **THEN** the rolling win-rate chart nav item does NOT appear in the sidebar

#### Scenario: Flag enabled — link visible
- **WHEN** `rolling_winrate_chart` flag is `true`
- **THEN** the rolling win-rate chart nav item appears in the sidebar under the PERFORMANCE group

### Requirement: MAE/MFE flag is a reserved placeholder
The `mae_mfe` flag SHALL be listed in the features settings UI with a label and description, but its toggle SHALL be disabled (greyed out) until the MAE/MFE feature is implemented. The toggle SHALL display a "(coming soon)" badge.

#### Scenario: MAE/MFE toggle is disabled
- **WHEN** the user views the Features section in Settings
- **THEN** the `mae_mfe` toggle row is visible but the switch is disabled and not interactive
- **AND** a "(coming soon)" indicator is shown next to the label
