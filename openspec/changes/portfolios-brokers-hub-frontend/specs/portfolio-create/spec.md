## ADDED Requirements

### Requirement: User can create a portfolio via a modal dialog
The hub SHALL provide a "Create New Portfolio" modal that captures name, base currency, and color. The modal SHALL display a prominent warning that base currency cannot be changed after creation. On success, the new portfolio SHALL appear in the hub accordion.

#### Scenario: Create portfolio modal opens
- **WHEN** the user clicks "Create New Portfolio" button in the hub
- **THEN** a modal dialog opens with fields: Portfolio Name (text input), Base Currency (select, default USD), and Color (chip picker)

#### Scenario: Currency immutability warning is displayed
- **WHEN** the create modal is open
- **THEN** a warning notice reads "The base currency cannot be changed after the portfolio is created. It serves as the foundation for all performance metrics."

#### Scenario: Successful portfolio creation
- **WHEN** the user fills in a valid name, selects a currency, picks a color, and clicks "Create Portfolio"
- **THEN** the system calls `POST /api/v1/portfolios` and the new portfolio appears in the hub accordion; the modal closes

#### Scenario: Create portfolio — name required
- **WHEN** the user submits the form with an empty name
- **THEN** the form shows a validation error "Portfolio name is required" and does not submit

#### Scenario: Color chip picker shows fixed palette
- **WHEN** the create modal is open
- **THEN** a row of color chips from PORTFOLIO_COLORS is shown; clicking one selects it with a ring/border visual; the selected chip's hex value is submitted as `color_hex`

#### Scenario: Cancel closes modal without saving
- **WHEN** the user clicks "Cancel" or presses Escape
- **THEN** the modal closes and no API call is made
