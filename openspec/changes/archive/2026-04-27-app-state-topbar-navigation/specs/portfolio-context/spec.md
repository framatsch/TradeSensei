## ADDED Requirements

### Requirement: Application context stored in global state
The system SHALL maintain a single `activeContext` value (`'portfolio' |
'library' | 'checkin'`) in a Zustand store (`appContextStore`). This value
SHALL be the sole source of truth for which application mode is active.

#### Scenario: Initial hydration reads localStorage
- **WHEN** the application first mounts on the client
- **THEN** `appContextStore.hydrate()` reads `localStorage.getItem("active_app_context")`; if absent or invalid defaults to `'portfolio'`; sets `hydrated = true`

#### Scenario: Context persisted on change
- **WHEN** `setActiveContext(ctx)` is called
- **THEN** `activeContext` in the store is updated AND `localStorage.setItem("active_app_context", ctx)` is called

---

### Requirement: Active portfolio stored in global state
The system SHALL maintain a single `activePortfolioId` value (UUID string or
null) in a Zustand store (`portfolioStore`). This value SHALL be the sole
source of truth for which portfolio is currently active across the entire
frontend application.

#### Scenario: Initial hydration reads localStorage
- **WHEN** the application first mounts on the client
- **THEN** `portfolioStore.hydrate()` is called, reads `localStorage.getItem("active_portfolio_id")`, and sets `activePortfolioId` to the stored value (or `null` if absent); `hydrated` is set to `true`

#### Scenario: localStorage unavailable
- **WHEN** `localStorage.getItem` throws (e.g. private browsing restrictions)
- **THEN** `portfolioStore.hydrate()` catches the error, sets `activePortfolioId` to `null`, and sets `hydrated` to `true` without crashing

#### Scenario: Portfolio ID persisted on change
- **WHEN** `setActivePortfolioId(id)` is called with a valid UUID
- **THEN** `activePortfolioId` in the store is updated AND `localStorage.setItem("active_portfolio_id", id)` is called

---

### Requirement: Active portfolio resolves to a full portfolio object
The system SHALL provide a `useActivePortfolio` hook that resolves
`activePortfolioId` to a full `PortfolioRead` object by cross-referencing the
fetched portfolio list.

#### Scenario: Active ID matches a portfolio in the list
- **WHEN** `useActivePortfolio()` is called and the stored ID exists in the portfolio list
- **THEN** the hook returns `{ activePortfolioId: "<id>", activePortfolio: <PortfolioRead>, isLoading: false }`

#### Scenario: Active ID is stale (portfolio no longer exists)
- **WHEN** the stored `activePortfolioId` is not present in the fetched portfolio list AND the list is non-empty
- **THEN** the hook silently sets `activePortfolioId` to `portfolios[0].id`, updates localStorage, and returns the first portfolio as `activePortfolio`

#### Scenario: Loading state before hydration or fetch completes
- **WHEN** either `portfolioStore.hydrated` is `false` OR the portfolio list fetch is in-flight
- **THEN** `isLoading` is `true` and `activePortfolio` is `null`

---

### Requirement: Dashboard pages consume active portfolio via hook only
All dashboard pages and components that require portfolio context SHALL call
`useActivePortfolio()` to obtain `activePortfolioId`. They SHALL NOT import
from `portfolioStore` directly.

#### Scenario: Page reads active portfolio for API calls
- **WHEN** a dashboard page needs to call a portfolio-scoped API endpoint
- **THEN** it reads `activePortfolioId` from `useActivePortfolio()` and passes it to the relevant data hook (e.g. `useTrades(activePortfolioId)`)

#### Scenario: Page renders loading skeleton while portfolio is resolving
- **WHEN** `isLoading` is `true` from `useActivePortfolio()`
- **THEN** the page renders a skeleton / loading state and does NOT call portfolio-scoped API hooks with a null ID
