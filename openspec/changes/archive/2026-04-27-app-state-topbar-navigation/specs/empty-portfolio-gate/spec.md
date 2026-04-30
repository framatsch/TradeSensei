## ADDED Requirements

### Requirement: Empty portfolio gate intercepts dashboard when no portfolios exist
The system SHALL intercept the normal dashboard shell render when
`portfolios.length === 0` (after a successful portfolio list fetch) and display
an `EmptyPortfolioGate` component instead of `{children}`.

#### Scenario: No portfolios after successful fetch
- **WHEN** the user is authenticated AND the `GET /portfolios` request succeeds AND the response contains zero portfolios
- **THEN** the dashboard layout renders `EmptyPortfolioGate` with a CTA to create the first portfolio; no page content (`{children}`) is rendered

#### Scenario: Portfolio fetch in flight
- **WHEN** `usePortfolios()` is still loading (before the first response)
- **THEN** the dashboard layout renders a loading skeleton; the gate is NOT shown prematurely

#### Scenario: Portfolio fetch fails with network or server error
- **WHEN** `usePortfolios()` returns an error state
- **THEN** the dashboard layout renders an error banner (e.g. "Failed to load portfolios — please refresh"); the empty gate is NOT shown

---

### Requirement: EmptyPortfolioGate provides a clear path to create a portfolio
The `EmptyPortfolioGate` component SHALL display a clear message explaining
that no portfolio exists yet and SHALL provide a single primary call-to-action
that navigates to the portfolio creation flow.

#### Scenario: CTA navigates to portfolio settings
- **WHEN** the user clicks the primary CTA in EmptyPortfolioGate
- **THEN** the user is navigated to `/dashboard/settings?tab=portfolios`

#### Scenario: Gate does not show sidebar navigation
- **WHEN** EmptyPortfolioGate is rendered
- **THEN** the sidebar navigation links are NOT visible (the gate is a full-content replacement, not an overlay); the TopBar IS visible so the user can still sign out
