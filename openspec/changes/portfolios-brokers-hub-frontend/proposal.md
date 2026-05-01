## Why

The platform has a working backend with portfolio and account management APIs, but the frontend lacks a unified settings UI where users can configure their capital structure. Users currently cannot create portfolios, link broker accounts, or manage their capital hierarchy through the UI — this is a critical gap for any meaningful use of the platform.

## What Changes

- Add a "Portfolios & Brokers" tab to the System Settings modal
- Implement a nested accordion/tree-view layout showing Portfolios as parent nodes and Broker Accounts as child nodes
- Add Portfolio creation modal (name, base_currency, color_hex) with immutability warning on currency
- Add Portfolio edit modal (name, color_hex only; base_currency read-only) with high-friction cascading delete (user must type portfolio name)
- Add Broker Account creation modal (display name, type, credentials, sync start date) with context-injected portfolio_id
- Add Broker Account edit modal (name editable; type immutable; credentials masked; deactivate action)
- Add non-blocking "Test Connection" inline action for broker accounts
- Manage accordion expanded/collapsed state in local UI state decoupled from server data

## Capabilities

### New Capabilities
- `portfolios-brokers-hub`: The main settings tab component — nested accordion hub displaying portfolios and their linked broker accounts with add/edit actions
- `portfolio-create`: Portfolio creation modal with name, base_currency (immutable warning), and color_hex fields
- `portfolio-edit`: Portfolio edit modal with name/color_hex editing, read-only base_currency, and high-friction cascading delete danger zone
- `broker-account-create`: Broker account creation modal with auto-injected portfolio_id, dynamic auth fields by broker type, test connection, and sync start date
- `broker-account-edit`: Broker account edit modal with immutable type badge, masked credentials, test connection, and deactivate action

### Modified Capabilities
- `portfolio-settings`: The existing settings modal gains the new "Portfolios & Brokers" tab

## Impact

- **Frontend**: New settings tab and 5 new modal components in the frontend app
- **API client**: Uses existing generated OpenAPI client endpoints for portfolios and accounts (no new backend endpoints required)
- **State**: Local accordion expansion state managed independently of TanStack Query cache
- **Dependencies**: Existing `portfolio-management` and `account-management` backend APIs; color picker library (e.g., `react-colorful`)
