## Context

Currently, the `TradeChart` component hardcodes the `["1h", "4h", "1d"]` intervals for displaying trade data. However, market data providers configured in the MarketDataHub might not support intraday resolutions (e.g., they might only support daily EOD data). When a user relies on such a provider, displaying "1h" and "4h" buttons leads to empty charts or broken requests, providing a poor user experience.

We want to allow users to configure which chart intervals should be displayed in the UI, tying it directly to their user settings in the backend. 

## Goals / Non-Goals

**Goals:**
- Add `chart_intervals` to user settings to manage visible chart resolutions.
- Update `TradeChart.tsx` to read the configured intervals and handle default selection gracefully when "1h" or "4h" are omitted.
- Expose this setting in the Settings Page under General or Features settings.

**Non-Goals:**
- Do not automatically detect the MarketDataHub provider capabilities. We leave this as a manual user setting for simplicity.
- Do not change how the charts fetch data, just which interval buttons are available and what the default interval is.

## Decisions

**Decision 1: Backend schema for `chart_intervals`**
- **Choice:** Add `chart_intervals: list[Literal["1h", "4h", "1d"]]` to `UserSettingsRead` and `UserSettingsUpdate`.
- **Rationale:** Pydantic handles lists perfectly. The database stores the settings as key-value pairs (as stringified JSON or plain text depending on implementation, but in this case `user_settings` table uses `key`/`value` rows). Wait, the `user_settings` table stores values as `Text`. We need to serialize/deserialize it in the backend or frontend. Actually, `useUpdateSettings` sends `features` as a dict which is mapped. `chart_intervals` could be serialized to a JSON array string `["1h", "4h", "1d"]` in the DB.
Wait, let's look at `UserSetting` model. It has `key` and `value`. So `key="chart_intervals"`, `value="[\"1h\", \"4h\", \"1d\"]"`. We will need to update the repository logic. Actually, looking at `frontend/hooks/useSettings.ts`, `features` is a `Record<string, boolean>`. If we just add `chart_intervals` to the `UserSettingsRead` schema, we need to ensure the repository maps it. 
- **Alternative:** Just use a comma-separated string like `"1d"` or `"1h,4h,1d"`.
- **Selected approach:** We will use `list[str]` in Pydantic, and in `user_setting_repository.py` it will serialize to JSON string and parse back.

**Decision 2: UI for configuring intervals**
- **Choice:** Multi-select checkboxes or pill buttons in `GeneralSettings` or `FeaturesSettings` components.
- **Rationale:** Users can easily toggle "1h", "4h", "1d".

**Decision 3: Default Interval Logic**
- **Choice:** Update `smartDefaultInterval` in `TradeChart.tsx` to accept the allowed `Interval[]`. If the logic previously decided on "1h" but "1h" is not available, fallback to the next available resolution (e.g., "4h", then "1d").

## Risks / Trade-offs

- **Risk:** User deselects all intervals.
  - **Mitigation:** The frontend settings UI should require at least one interval to be selected, or default to `["1d"]` if the array is empty.
- **Risk:** The backend settings serialization logic gets complicated.
  - **Mitigation:** Follow the existing pattern used for the `features` dictionary, which must already serialize to JSON.
