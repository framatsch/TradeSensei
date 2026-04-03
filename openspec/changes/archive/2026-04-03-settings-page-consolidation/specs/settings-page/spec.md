## ADDED Requirements

### Requirement: Settings page is accessible at /dashboard/settings
The frontend SHALL provide a Settings page at `/dashboard/settings`. The sidebar navigation SHALL include a "Settings" entry with a gear icon, placed at the bottom of the nav list. The existing "Accounts" and "Connections" nav entries SHALL be removed.

#### Scenario: Settings page renders
- **WHEN** an authenticated user navigates to `/dashboard/settings`
- **THEN** the page loads with two visible tabs: "General" and "Accounts & Integrations"

#### Scenario: Old routes redirect
- **WHEN** a user navigates to `/dashboard/accounts`
- **THEN** they are redirected to `/dashboard/settings`
- **WHEN** a user navigates to `/dashboard/connections`
- **THEN** they are redirected to `/dashboard/settings`

#### Scenario: Settings link appears in sidebar
- **WHEN** the sidebar is rendered
- **THEN** a "Settings" link with a gear icon is present
- **AND** "Accounts" and "Connections" links are no longer present

### Requirement: General tab manages UI preferences
The General tab SHALL contain controls for:
1. **Theme**: A segmented control or radio group with options "System", "Light", "Dark". Selecting a value SHALL immediately apply the theme and save it via `PUT /users/me/settings`.
2. **Default Date Range**: A dropdown/select with options "All Time", "Year to Date", "Last 30 Days". Changing the value SHALL save it via `PUT /users/me/settings`.

#### Scenario: Theme toggle applies immediately
- **WHEN** the user selects "Dark" in the theme control
- **THEN** the UI switches to dark mode immediately (without page reload)
- **AND** the preference is saved to the server

#### Scenario: Settings load persisted values
- **WHEN** the user opens the General tab
- **THEN** the theme control reflects the user's saved theme preference
- **AND** the date range dropdown reflects the user's saved default_date_range

### Requirement: Accounts & Integrations tab consolidates accounts and broker connections
The Accounts & Integrations tab SHALL contain two sections:

**Section 1 — Accounts**: A list of the user's trading accounts (same functionality as the current `/dashboard/accounts` page). The user SHALL be able to create, rename, and delete accounts. Accounts show their broker type, currency, and active status.

**Section 2 — Broker Integrations**: Cards for each supported broker:
- **Schwab**: Shows OAuth connection status. Renders the existing `SchwabConnectionCard` component.
- **IBKR**: Shows Flex Query connection status. Renders a new `IBKRConnectionCard` component.

#### Scenario: Account list is visible
- **WHEN** the user opens Settings → Accounts & Integrations
- **THEN** all their accounts are listed with name, broker, and currency

#### Scenario: New account can be created
- **WHEN** the user clicks "Add Account" in the Accounts section
- **THEN** a form appears for account name, broker type, and currency
- **AND** submitting it creates the account and adds it to the list

#### Scenario: Broker integration cards are visible
- **WHEN** the user opens Settings → Accounts & Integrations
- **THEN** a Schwab card and an IBKR card are both visible in the Integrations section
