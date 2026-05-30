## ADDED Requirements

### Requirement: show_open_trades setting stored per user
The backend `UserSettingsRead` schema SHALL expose a `show_open_trades` boolean field (default: `false`).
`UserSettingsUpdate` SHALL accept `show_open_trades` as an optional partial-update input.
The backend service SHALL read and write the value using the key `"show_open_trades"` in the existing `features` JSONB column of the `user_settings` table. No DB migration is required.

#### Scenario: Default value when not set
- **WHEN** `GET /api/v1/users/me/settings` is called and `show_open_trades` has never been saved
- **THEN** the response includes `show_open_trades: false`

#### Scenario: User enables show_open_trades
- **WHEN** `PUT /api/v1/users/me/settings` is called with `{"features": {"show_open_trades": true}}`
- **THEN** the value is persisted and a subsequent `GET` returns `show_open_trades: true`

#### Scenario: Partial update preserves other feature flags
- **WHEN** `PUT /api/v1/users/me/settings` is called with only `{"features": {"show_open_trades": true}}`
- **THEN** other feature flag values (e.g. `risk_analytics`) are unchanged

### Requirement: Trade lists enforce closed-only when show_open_trades is disabled
When `show_open_trades = false`, all trade list API calls (dashboard widgets, workspace tables, trades page) SHALL have `status=closed` applied regardless of any filter state. The status filter parameter from URL or local state SHALL be silently ignored and not forwarded to the API.

#### Scenario: Setting off — open status param is ignored
- **WHEN** `show_open_trades = false` AND the URL contains `?status=open`
- **THEN** the API is called with `status=closed` and only closed trades are returned
- **AND** an info banner is shown: "Open trades are hidden. Enable 'Show Open Trades' in Settings → UI to show them."

#### Scenario: Setting off — no status param always defaults to closed
- **WHEN** `show_open_trades = false` AND no `status` param is present in the URL
- **THEN** the API is called with `status=closed`

#### Scenario: Setting on — status param is forwarded normally
- **WHEN** `show_open_trades = true` AND the URL contains `?status=open`
- **THEN** the API is called with `status=open` and open trades are returned

#### Scenario: Setting on — default shows all trades
- **WHEN** `show_open_trades = true` AND no `status` param is present
- **THEN** the API is called without a status filter and all trades are returned

### Requirement: Open/Closed filter toggle visibility controlled by setting
The Open/Closed/All filter toggle in all trade list filter bars SHALL be conditionally rendered based on `show_open_trades`. When `false`, the toggle SHALL NOT be rendered. When `true`, the toggle SHALL be rendered and functional.

#### Scenario: Toggle hidden when setting is off
- **WHEN** `show_open_trades = false`
- **THEN** the Open/Closed/All filter toggle is not visible in the filter bar of any trade list view

#### Scenario: Toggle visible and functional when setting is on
- **WHEN** `show_open_trades = true`
- **THEN** the Open/Closed/All filter toggle is rendered in the filter bar
- **AND** selecting "Open" updates the URL with `?status=open` and fetches open trades
- **AND** selecting "Closed" updates the URL with `?status=closed` and fetches closed trades
- **AND** selecting "All" removes the status param and fetches all trades

### Requirement: show_open_trades toggle in UI Settings (Features tab)
The Settings page Features tab SHALL include a toggle for `show_open_trades` using the existing deferred Apply pattern.

#### Scenario: Toggle renders with correct state
- **WHEN** the user opens Settings → Features
- **THEN** a "Show Open Trades" toggle is shown with label and description: "Show open positions in trade lists and enable the Open/Closed filter."
- **AND** the toggle reflects the current server value of `show_open_trades`

#### Scenario: User enables and applies
- **WHEN** the user flips the toggle to enabled and clicks "Apply Changes"
- **THEN** `PUT /api/v1/users/me/settings` is called with `{"features": {"show_open_trades": true}}`
- **AND** trade list views immediately respect the new setting

#### Scenario: Apply button disabled with no changes
- **WHEN** the user has not changed the toggle value
- **THEN** the "Apply Changes" button is disabled

### Requirement: Help page documents show_open_trades setting
The Help page SHALL include documentation for the `show_open_trades` setting explaining its effect on trade list visibility and the filter toggle.

#### Scenario: Help entry exists and is accurate
- **WHEN** the user navigates to the Help page and looks for trade filter documentation
- **THEN** an entry explains that "Show Open Trades" is off by default and only closed trades are shown
- **AND** the entry explains how to enable it to see open trades and the Open/Closed filter toggle
