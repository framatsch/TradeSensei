# chart-display-settings Specification

## Purpose
Define expected behavior for user-configurable chart display defaults and the Look & Feel settings tab.

## Requirements

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

---

### Requirement: Home page preference stored in user settings
The backend `UserSettingsRead` schema SHALL expose a `home_route` field
(`str`, default `"/dashboard"`). `UserSettingsUpdate` SHALL accept it as an
optional field. The backend service SHALL read and write it using the key
`"home_route"` in `user_settings`. Valid values are exactly:
`"/dashboard"` (Portfolio Overview), `"/dashboard/trades"` (Journal),
`"/dashboard/library"` (Strategy & Tags). Any other stored value SHALL be
treated as `"/dashboard"` at read time.

#### Scenario: Read default when no value stored
- **WHEN** `GET /api/v1/users/me/settings` is called and `"home_route"` does not exist in `user_settings`
- **THEN** the response includes `home_route: "/dashboard"`

#### Scenario: Write and read back a custom home route
- **WHEN** `PUT /api/v1/users/me/settings` is called with `{"home_route": "/dashboard/trades"}`
- **THEN** the key is upserted and a subsequent `GET` returns `home_route: "/dashboard/trades"`

#### Scenario: Invalid stored value falls back to default
- **WHEN** `user_settings` contains `home_route = "/dashboard/invalid"`
- **THEN** `GET /api/v1/users/me/settings` returns `home_route: "/dashboard"`

### Requirement: Look & Feel tab exposes home page preference
The **Look & Feel** settings tab SHALL include a "Default Home Page" select
field with three options: "Portfolio Overview" (`/dashboard`), "Journal"
(`/dashboard/trades`), "Strategy & Tags" (`/dashboard/library`).

```
+-------------------------------------------------------+
|  Look & Feel                                          |
|  ─────────────────────────────────────────────────    |
|  Candles before entry:  [ 20 ]                        |
|  Candles after exit:    [ 10 ]                        |
|  Show post-exit candles by default:  ( Off )          |
|                                                       |
|  Default Home Page:                                   |
|  [ Portfolio Overview           ▼ ]                   |
|    ○ Portfolio Overview                               |
|    ○ Journal                                          |
|    ○ Strategy & Tags                                  |
+-------------------------------------------------------+
```

#### Scenario: Select renders current value
- **WHEN** the user opens the Look & Feel tab and `home_route` is `"/dashboard/trades"`
- **THEN** the "Default Home Page" select shows "Journal" as the selected option

#### Scenario: User changes home page and saves
- **WHEN** the user selects "Strategy & Tags" and clicks Save
- **THEN** `PUT /api/v1/users/me/settings` is called with `{"home_route": "/dashboard/library"}` and a success toast is shown

#### Scenario: TopBar wordmark reflects saved home route immediately
- **WHEN** the user saves a new `home_route` value
- **THEN** the TanStack Query `["users","me","settings"]` cache is invalidated so the wordmark link target updates on next render without a page reload
