## ADDED Requirements

### Requirement: Features flag stored in user settings
The backend SHALL store a `features` field as a JSON object (string keys, boolean values) in the `user_settings` table under the key `"features"`. The `UserSettingsRead` schema SHALL include a `features` field of type `dict[str, bool]` that defaults to an empty dict `{}` when the key is absent. The `UserSettingsUpdate` schema SHALL accept an optional `features` field; when provided it SHALL be merged with (not replace) the existing flags map so that partial updates are safe.

#### Scenario: Read settings when no features key exists
- **WHEN** `GET /api/v1/users/me/settings` is called and no `"features"` row exists in `user_settings` for that user
- **THEN** the response includes `"features": {}` (empty object, not null)

#### Scenario: Read settings when features key exists
- **WHEN** a `"features"` row exists with value `{"rolling_winrate_chart": true}`
- **THEN** `GET /api/v1/users/me/settings` returns `"features": {"rolling_winrate_chart": true}`

#### Scenario: Update a single flag without affecting others
- **WHEN** `PUT /api/v1/users/me/settings` is sent with `{"features": {"mae_mfe": true}}`
- **AND** the existing features map is `{"rolling_winrate_chart": true}`
- **THEN** the resulting features map is `{"rolling_winrate_chart": true, "mae_mfe": true}` (merge, not overwrite)

#### Scenario: Set a flag to false
- **WHEN** `PUT /api/v1/users/me/settings` is sent with `{"features": {"rolling_winrate_chart": false}}`
- **THEN** the response includes `"features": {"rolling_winrate_chart": false}`

#### Scenario: Invalid features value is rejected
- **WHEN** `PUT /api/v1/users/me/settings` is sent with `{"features": "not-an-object"}`
- **THEN** the API returns HTTP 422 Unprocessable Entity

### Requirement: Features update is idempotent
Sending the same `PUT` request twice with the same `features` payload SHALL produce the same result as sending it once — no duplicate rows or errors.

#### Scenario: Repeated update
- **WHEN** `PUT /api/v1/users/me/settings` is called twice with `{"features": {"rolling_winrate_chart": true}}`
- **THEN** both responses return HTTP 200 with `"features": {"rolling_winrate_chart": true}`

## MODIFIED Requirements

### Requirement: User settings schema
The `UserSettingsRead` response object SHALL include `theme`, `default_date_range`, AND `features`. The `UserSettingsUpdate` request object SHALL accept any combination of `theme`, `default_date_range`, and `features` (all optional).

#### Scenario: Full settings read
- **WHEN** `GET /api/v1/users/me/settings` is called
- **THEN** the response data object contains exactly the keys: `theme`, `default_date_range`, `features`

#### Scenario: Partial update (theme only)
- **WHEN** `PUT /api/v1/users/me/settings` is sent with `{"theme": "dark"}` only
- **THEN** the `features` map in the response is unchanged
