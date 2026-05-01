## ADDED Requirements

### Requirement: User can create a broker account scoped to a portfolio via a modal dialog
The hub SHALL provide a "Connect Broker Account" modal. When opened from within an expanded portfolio, the target portfolio SHALL be displayed as read-only context and its `portfolio_id` SHALL be automatically injected into the request. The user SHALL NOT manually select the parent portfolio.

#### Scenario: Create modal opened from portfolio context
- **WHEN** the user clicks "Add Broker Account to this Portfolio" under an expanded portfolio
- **THEN** the modal opens showing "Target Portfolio: [Portfolio Name]" as read-only text, with `portfolio_id` pre-set

#### Scenario: Broker type selection determines auth fields
- **WHEN** the user selects "IBKR" as broker type
- **THEN** the Authentication section shows "Flex Token" and "Flex Query ID" fields

#### Scenario: Broker type Schwab shows correct auth fields
- **WHEN** the user selects "Schwab" as broker type
- **THEN** the Authentication section shows "App Key" and "App Secret" fields

#### Scenario: Broker type Manual shows no auth fields
- **WHEN** the user selects "Manual" as broker type
- **THEN** the Authentication section is hidden or shows a notice "No credentials required for manual accounts"

#### Scenario: Successful broker account creation
- **WHEN** the user fills in Display Name, selects Broker Type, optionally enters credentials and sync start date, and clicks "Connect Account"
- **THEN** the system calls `POST /api/v1/portfolios/{portfolio_id}/accounts` and the new account appears under the parent portfolio in the hub; the modal closes

#### Scenario: Display name is required
- **WHEN** the user submits the form with an empty display name
- **THEN** the form shows "Account name is required" and does not submit

### Requirement: Test Connection provides non-blocking inline feedback
The broker account create modal SHALL include a "Test Connection" button that calls the test connection endpoint. A failure result SHALL display an inline error message but SHALL NOT disable the primary Save/Connect button.

#### Scenario: Test connection success
- **WHEN** the user clicks "Test Connection" and the API returns success
- **THEN** an inline green success indicator appears: "Connection successful"

#### Scenario: Test connection failure — Save remains enabled
- **WHEN** the user clicks "Test Connection" and the API returns an error
- **THEN** an inline red error message shows the failure reason, but the "Connect Account" button remains enabled

#### Scenario: Test connection while pending
- **WHEN** the test connection request is in-flight
- **THEN** the "Test Connection" button shows a loading spinner and is temporarily disabled

### Requirement: Sync start date configuration
The broker account create modal SHALL include an Import Settings section with a date field for specifying the historical data sync start date.

#### Scenario: Sync start date defaults to current year start
- **WHEN** the create modal opens
- **THEN** the sync start date defaults to January 1 of the current year

#### Scenario: User changes sync start date
- **WHEN** the user picks a different date
- **THEN** the selected date is submitted as the `flex_from_date` or equivalent field in the create payload
