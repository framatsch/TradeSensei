## ADDED Requirements

### Requirement: Hub displays portfolios as accordion parent nodes with child accounts
The Portfolios & Brokers hub SHALL render each portfolio as an expandable accordion row. When expanded, the portfolio node SHALL list all linked broker accounts as child rows. The hub SHALL display a "Create New Portfolio" button at the top level.

#### Scenario: Accordion is collapsed by default
- **WHEN** the user opens the Portfolios & Brokers tab
- **THEN** all portfolio accordion nodes are collapsed, showing only portfolio name, base currency, color indicator, and an Edit button

#### Scenario: Expanding a portfolio shows linked accounts
- **WHEN** the user clicks the expand chevron/arrow on a portfolio row
- **THEN** the portfolio node expands to show a list of its linked broker accounts (name, type badge, connection status) and an "Add Broker Account" button

#### Scenario: Collapsed by default with one exception
- **WHEN** the hub loads and there is exactly one portfolio
- **THEN** that portfolio's accordion is auto-expanded

#### Scenario: Expanding does not collapse on background refetch
- **WHEN** the user has expanded a portfolio and a TanStack Query refetch occurs (e.g., after adding a child account)
- **THEN** the accordion remains expanded without collapsing

#### Scenario: Account status indicator shown per account
- **WHEN** an account is listed under an expanded portfolio
- **THEN** each account row shows a status badge: "Connected" (green), "Error" (amber with warning icon), or "Inactive" (muted) based on the account's `is_active` flag and last sync status

### Requirement: Hub tab replaces the separate Portfolios and Accounts & Integrations tabs
The Settings page SHALL replace the existing "Portfolios" and "Accounts & Integrations" tabs with a single "Portfolios & Brokers" tab. The legacy `?tab=portfolios` and `?tab=integrations` URL params SHALL redirect to the new tab.

#### Scenario: Single tab shown in settings tab bar
- **WHEN** the user opens System Settings
- **THEN** the tab bar shows "Portfolios & Brokers" instead of separate "Portfolios" and "Accounts & Integrations" tabs

#### Scenario: Legacy URL params activate the new tab
- **WHEN** the user navigates to settings with `?tab=portfolios` or `?tab=integrations`
- **THEN** the "Portfolios & Brokers" tab is activated
