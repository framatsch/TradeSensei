## MODIFIED Requirements

### Requirement: Accounts tab scoped to active portfolio
The Accounts & Integrations tab in Settings SHALL filter the account list to only show accounts
belonging to the **active portfolio** (`activePortfolioId` from the Zustand store). If no active
portfolio is set (e.g. Spec 2 not yet applied, or portfolios list is empty) the tab SHALL fall
back to showing all accounts owned by the user.

#### Scenario: Accounts list scoped when active portfolio is set
- **WHEN** the user opens the Accounts & Integrations tab and `activePortfolioId` is a valid UUID
- **THEN** `useAccounts(portfolioId)` is called with that UUID and only accounts belonging to that portfolio are displayed

#### Scenario: Accounts list falls back when no active portfolio
- **WHEN** `activePortfolioId` is null or the portfolio list fails to load
- **THEN** `useAccounts()` is called without a `portfolioId` and all user accounts are displayed (graceful degradation)

#### Scenario: Create account assigns to active portfolio
- **WHEN** the user creates a new account from the Accounts & Integrations tab and `activePortfolioId` is set
- **THEN** the `AccountForm` pre-fills `portfolio_id` with `activePortfolioId` and the POST request includes it

#### Scenario: Account portfolio label shown
- **WHEN** accounts from multiple portfolios are shown (fallback mode)
- **THEN** each account row displays the portfolio name it belongs to
