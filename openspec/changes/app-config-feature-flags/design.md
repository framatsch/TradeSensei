## Context

The application uses a `user_settings` table (key-value store) to persist per-user preferences: `theme` and `default_date_range`. These are surfaced via `GET/PUT /api/v1/users/me/settings`, with typed Pydantic schemas (`UserSettingsRead`, `UserSettingsUpdate`) and a `useSettings` React Query hook.

There is currently no mechanism to toggle individual features on or off. The project has several opt-in capabilities either already built (rolling win-rate chart) or planned (MAE/MFE metrics) that should not be visible to all users by default — either because they are experimental, incomplete, or simply add clutter for users who do not need them.

## Goals / Non-Goals

**Goals:**
- Store a `features` object (string → boolean flags) per user in the existing `user_settings` KV table under the key `"features"`
- Expose the flags through the existing settings API with zero new endpoints
- Provide a `useFeatureFlag(key)` React hook that reads from the TanStack Query settings cache (no extra fetches)
- Show a "Features" section in the General Settings tab where users can toggle each known flag
- Gate the rolling win-rate chart sidebar link behind a flag as the first integration

**Non-Goals:**
- Server-side feature gating (backend does not check flags before returning data)
- Admin-controlled global flags or rollout percentages
- A/B testing infrastructure
- Flags stored in environment variables or build-time config

## Decisions

### Decision 1: Store flags as a JSON string in the existing KV table (key `"features"`)

**Rationale**: No new migration needed. The `user_settings` table already has a `Text` value column; storing `{"rolling_winrate_chart": true}` under the `"features"` key reuses the existing upsert/merge logic. The alternative — adding a dedicated `user_feature_flags` table — would require a migration, a new repository method, and a new API endpoint for no meaningful gain at this stage.

**Alternative considered**: A separate `UserFeatureFlag` model with one row per flag. Rejected because it adds schema complexity and a migration for what is essentially a serialized boolean map.

### Decision 2: Known flags defined as a typed constant on the frontend only

**Rationale**: The backend treats the `features` value as an opaque JSON blob — it validates that it is a valid JSON object of booleans, but has no hard-coded list of keys. The canonical list of flags lives in `frontend/lib/featureFlags.ts` as a TypeScript `const` object with descriptions. This keeps the backend dumb and allows adding new flags without a backend deploy or migration.

**Alternative considered**: An enum or list of allowed flag keys enforced by the backend. Rejected because it adds tight coupling between backend and frontend for a purely UI concern.

### Decision 3: Flags default to `false` (opt-in model)

**Rationale**: New features start hidden. Users who want them explicitly enable them. This avoids sudden UI changes for existing users on upgrade. The `useFeatureFlag` hook returns `false` when no `features` key exists in the user's settings yet.

### Decision 4: `useFeatureFlag` reads from the TanStack Query settings cache

**Rationale**: Settings are already fetched on app load by `useSettings`. A `useFeatureFlag(key)` hook can call `useQueryClient().getQueryData(SETTINGS_KEY)` synchronously — zero extra network requests. The alternative (a Zustand store) would duplicate state already managed by TanStack Query.

## Risks / Trade-offs

- **JSON blob opacity**: The backend cannot validate individual flag keys, so a typo in a flag key silently has no effect. Mitigation: the frontend `FEATURE_FLAGS` constant is the single source of truth; all flag reads go through `useFeatureFlag(key)` which is keyed against that constant.
- **Stale flags after logout/login on shared machine**: Settings cache is per-session. Mitigation: `useSettings` has a 5-minute `staleTime` and refetches on window focus — adequate for this use case.
- **Flags are user-visible toggles, not security controls**: A determined user could enable a flag via the API. This is acceptable — flags control UI visibility of finished but optional features, not access to privileged data.

## Migration Plan

1. Backend: update `UserSettingsRead` / `UserSettingsUpdate` to include `features: dict[str, bool]`; update service to merge the `features` blob on upsert
2. Frontend: add `lib/featureFlags.ts`, `useFeatureFlag` hook, `FeaturesSettings` component, integrate into `GeneralSettings`
3. Integrate first flag gate: rolling win-rate chart sidebar link (hidden unless `rolling_winrate_chart` flag is `true`)
4. No database migration required — existing rows without a `"features"` key simply return `{}` (empty map), which the frontend treats as all flags `false`
5. Rollback: remove the `features` field from the schema — clients that still send it receive a 422, but existing data in the KV store is harmless

## Open Questions

- Should the **rolling win-rate chart** sidebar link be hidden by default for all users (opt-in), or visible by default with a flag to hide it (opt-out)? → Proposal says opt-in (`false` by default).
- Should the **MAE/MFE** flag be included now as a placeholder even though the feature does not exist yet? → Yes — it acts as a reserved flag name and prevents future naming conflicts.
