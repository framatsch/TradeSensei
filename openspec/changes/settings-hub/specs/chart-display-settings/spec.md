## ADDED Requirements

### Requirement: Chart display defaults stored in user settings
The backend `UserSettingsRead` schema SHALL expose three new fields:
- `chart_candles_before` (int, default 20) — number of candles to show before entry
- `chart_candles_after` (int, default 10) — number of candles to show after exit
- `chart_show_post_exit` (bool, default false) — whether post-exit candles are shown by default

`UserSettingsUpdate` SHALL accept the same three fields as optional partial-update inputs.
The backend service SHALL read and write these values using the keys `"chart_candles_before"`,
`"chart_candles_after"`, and `"chart_show_post_exit"` in the existing `user_settings` table.

#### Scenario: Read defaults when no value stored
- **WHEN** `GET /api/v1/users/me/settings` is called and none of the three keys exist in `user_settings`
- **THEN** the response body includes `chart_candles_before: 20`, `chart_candles_after: 10`, `chart_show_post_exit: false`

#### Scenario: Write and read back custom values
- **WHEN** `PUT /api/v1/users/me/settings` is called with `{"chart_candles_before": 30, "chart_candles_after": 5, "chart_show_post_exit": true}`
- **THEN** the keys are upserted in `user_settings` and a subsequent `GET` returns the updated values

#### Scenario: Partial update preserves existing values
- **WHEN** `PUT /api/v1/users/me/settings` is called with only `{"chart_candles_before": 15}`
- **THEN** only `chart_candles_before` is updated; `chart_candles_after` and `chart_show_post_exit` retain their previous values

### Requirement: Look & Feel tab in Settings
The Settings Hub SHALL provide a **Look & Feel** tab that lets a user read and update the chart
display defaults.

#### Scenario: Look & Feel tab renders current values
- **WHEN** the user opens the Look & Feel tab
- **THEN** the form shows the current `chart_candles_before`, `chart_candles_after`, and `chart_show_post_exit` values fetched from `GET /api/v1/users/me/settings`

#### Scenario: User updates candle counts
- **WHEN** the user changes the "Candles before entry" or "Candles after exit" input and saves
- **THEN** `PUT /api/v1/users/me/settings` is called with the updated values and a success toast is shown

#### Scenario: Candle count validation — positive integer required
- **WHEN** the user enters a value ≤ 0 or a non-integer in a candle count field
- **THEN** the form shows an inline error "Must be a positive whole number" and save is disabled

#### Scenario: User toggles post-exit candle visibility
- **WHEN** the user changes the "Show post-exit candles by default" toggle and saves
- **THEN** `PUT /api/v1/users/me/settings` is called with the updated boolean and the toggle reflects the saved state

#### Scenario: Save fails — network error
- **WHEN** the PUT request fails
- **THEN** an error toast is shown and the form values revert to the last saved state
