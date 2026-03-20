## ADDED Requirements

### Requirement: User settings are persisted server-side
The system SHALL store per-user UI preferences in a `user_settings` table as key-value pairs. The backend SHALL expose `GET /users/me/settings` and `PUT /users/me/settings` endpoints, protected by JWT authentication. Settings that are not yet defined for a user SHALL return default values.

Supported keys and defaults:
- `theme`: `"system"` | `"light"` | `"dark"` — default: `"system"`
- `default_date_range`: `"all"` | `"ytd"` | `"last30"` — default: `"all"`

#### Scenario: Fetch settings for a new user
- **WHEN** an authenticated user calls `GET /users/me/settings` and has no saved settings
- **THEN** the response is `200 OK` with `{ "theme": "system", "default_date_range": "all" }`

#### Scenario: Save theme preference
- **WHEN** an authenticated user calls `PUT /users/me/settings` with `{ "theme": "dark" }`
- **THEN** the response is `200 OK` with the full settings object including `"theme": "dark"`
- **AND** subsequent `GET /users/me/settings` calls return the updated value

#### Scenario: Partial update preserves other keys
- **WHEN** a user has `{ "theme": "dark", "default_date_range": "ytd" }` saved
- **AND** calls `PUT /users/me/settings` with only `{ "theme": "light" }`
- **THEN** the response contains `{ "theme": "light", "default_date_range": "ytd" }`

#### Scenario: Invalid setting key is rejected
- **WHEN** an authenticated user calls `PUT /users/me/settings` with an unknown key (e.g. `{ "foo": "bar" }`)
- **THEN** the response is `422 Unprocessable Entity`

#### Scenario: Invalid setting value is rejected
- **WHEN** an authenticated user calls `PUT /users/me/settings` with `{ "theme": "purple" }`
- **THEN** the response is `422 Unprocessable Entity`

### Requirement: Frontend applies user settings on load
The frontend `useSettings` hook SHALL fetch settings on mount (after authentication). The trades page and dashboard SHALL use `default_date_range` as the initial filter when no URL query parameters are present.

#### Scenario: Default date range applied on trades page load
- **WHEN** the user has `default_date_range: "last30"` saved
- **AND** navigates to `/dashboard/trades` without URL parameters
- **THEN** the trade list is filtered to show only trades from the last 30 days
- **AND** the filter bar reflects the active date range

#### Scenario: URL parameters override user settings
- **WHEN** the user has `default_date_range: "last30"` saved
- **AND** navigates to `/dashboard/trades?opened_at_from=2020-01-01`
- **THEN** the URL parameter takes precedence and trades since 2020-01-01 are shown
