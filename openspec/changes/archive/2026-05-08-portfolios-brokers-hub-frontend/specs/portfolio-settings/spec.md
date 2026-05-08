## MODIFIED Requirements

### Requirement: User can manage portfolios from Settings
The Settings Hub SHALL provide a **Portfolios & Brokers** tab (replacing the former standalone **Portfolios** tab) that allows an authenticated user to create, edit, and delete their portfolios and manage their linked broker accounts from a single unified view.

#### Scenario: Create a portfolio
- **WHEN** the user fills in a portfolio name, selects a base currency, picks a colour chip, and submits the create portfolio modal
- **THEN** the system calls `POST /api/v1/portfolios` and the new portfolio appears in the hub accordion

#### Scenario: Create portfolio — duplicate name rejected
- **WHEN** the user submits a portfolio name that already exists for their account
- **THEN** the form shows an inline error "A portfolio with this name already exists" and does not navigate away

#### Scenario: Edit a portfolio name and colour
- **WHEN** the user clicks Edit on a portfolio row, changes the name or selects a different colour chip, and saves
- **THEN** the system calls `PATCH /api/v1/portfolios/{id}` with the updated fields

#### Scenario: Colour chip picker shows fixed palette
- **WHEN** the create or edit modal is open
- **THEN** a row of colour chip buttons from PORTFOLIO_COLORS is shown; clicking one selects it; the selected chip's hex value is submitted as `color_hex`

#### Scenario: Base currency is immutable after creation
- **WHEN** the portfolio edit modal is open
- **THEN** the base currency is displayed as read-only text and cannot be modified regardless of whether trades exist

#### Scenario: Base currency warning shown during creation
- **WHEN** the create portfolio modal is open
- **THEN** a notice warns "The base currency cannot be changed after the portfolio is created"

#### Scenario: Delete portfolio — requires typing portfolio name
- **WHEN** the user wants to delete a portfolio
- **THEN** the edit modal's Danger Zone requires them to type the exact portfolio name before the delete button is enabled

#### Scenario: Delete portfolio — cascading warning shown
- **WHEN** the Danger Zone section is visible
- **THEN** a red warning clearly states that all linked accounts and historical trades will be permanently deleted

### Requirement: User can set a default portfolio
The Portfolios & Brokers tab SHALL allow the user to designate one portfolio as the **default** — the portfolio automatically activated when entering Portfolio Workspace via the BentoMenu if no prior active portfolio is stored.

#### Scenario: Set a portfolio as default
- **WHEN** the user clicks the "Set as default" action (star icon) on a portfolio row
- **THEN** the system calls `PUT /api/v1/users/me/settings` with `{ "default_portfolio_id": "<id>" }` and the portfolio row shows a filled star indicator

#### Scenario: Only one portfolio can be default at a time
- **WHEN** the user sets portfolio B as default while portfolio A was previously default
- **THEN** only portfolio B shows the default indicator; portfolio A's indicator is cleared

#### Scenario: Default portfolio used on BentoMenu navigation
- **WHEN** the user clicks "Portfolio Workspace" in the BentoMenu and no `activePortfolioId` is stored in localStorage
- **THEN** `useActivePortfolio` reads `default_portfolio_id` from `user_settings` and activates that portfolio

#### Scenario: Default portfolio indicator visible in hub
- **WHEN** the Portfolios & Brokers tab is rendered
- **THEN** the portfolio matching `user_settings.default_portfolio_id` shows a filled star; if unset, no star is filled
