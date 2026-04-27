## MODIFIED Requirements

### Requirement: Account list is scoped to the active portfolio
Account management in the Settings page SHALL display and operate on accounts
that belong to the currently active portfolio (identified by `activePortfolioId`
from the global portfolio context). Accounts from other portfolios SHALL NOT be
shown.

#### Scenario: Settings accounts tab shows active portfolio accounts only
- **WHEN** the user navigates to `/dashboard/settings` on the Accounts tab
- **THEN** only accounts belonging to `activePortfolioId` are listed; accounts from other portfolios are not shown

#### Scenario: Create account links to active portfolio
- **WHEN** the user creates a new broker account via the Settings accounts tab
- **THEN** the account creation request includes `portfolio_id: activePortfolioId`

## REMOVED Requirements

### Requirement: Per-page account filter dropdown
**Reason**: The global portfolio context (active portfolio selected in TopBar)
replaces the per-page account filter. Filtering by individual account within a
portfolio is a lower-priority feature that may be re-introduced per-page later.
**Migration**: Pages that previously rendered `<AccountFilter>` and maintained
`accountId` local state should read `activePortfolioId` from `useActivePortfolio()`
instead and pass it to portfolio-scoped API hooks.
