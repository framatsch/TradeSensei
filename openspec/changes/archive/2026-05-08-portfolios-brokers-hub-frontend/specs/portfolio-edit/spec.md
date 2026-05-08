## ADDED Requirements

### Requirement: User can edit a portfolio name and color via a modal dialog
The hub SHALL provide a portfolio edit modal that allows editing name and color_hex only. Base currency SHALL be rendered as read-only text. The modal SHALL include a Danger Zone section for cascading portfolio deletion.

#### Scenario: Edit modal opens with pre-filled data
- **WHEN** the user clicks the Edit button on a portfolio row
- **THEN** a modal opens with the name field pre-filled, the color chip picker showing the current color, and base currency displayed as read-only text

#### Scenario: Base currency is read-only in edit mode
- **WHEN** the edit modal is open
- **THEN** base currency is rendered as a static text badge (not a select), and no input is provided to change it

#### Scenario: Saving name/color change succeeds
- **WHEN** the user modifies the name or selects a different color chip and clicks "Save Changes"
- **THEN** the system calls `PATCH /api/v1/portfolios/{id}` with the updated fields and the modal closes

### Requirement: Portfolio deletion requires typing the portfolio name to confirm
The portfolio edit modal SHALL include a Danger Zone section. To delete a portfolio, the user MUST type the exact portfolio name into a confirmation input before the delete button is enabled. The Danger Zone SHALL clearly warn that all linked accounts and historical trades will be permanently deleted.

#### Scenario: Danger Zone shows deletion warning
- **WHEN** the Danger Zone section is visible in the edit modal
- **THEN** a red-styled warning reads "This will permanently delete this portfolio, all linked broker accounts, and all historical trade data. This action cannot be undone."

#### Scenario: Delete button disabled until name matches
- **WHEN** the user has not typed anything or typed a partial/incorrect name in the confirmation input
- **THEN** the "Delete Portfolio" button is disabled and visually grayed out

#### Scenario: Delete button enabled after exact name match
- **WHEN** the user types the exact portfolio name (case-sensitive) into the confirmation input
- **THEN** the "Delete Portfolio" button becomes enabled

#### Scenario: Portfolio deletion executes on confirm
- **WHEN** the delete button is enabled and the user clicks "Delete Portfolio"
- **THEN** the system calls `DELETE /api/v1/portfolios/{id}`, the portfolio and all child data are removed, and the modal closes

#### Scenario: Confirmation input clears on modal close
- **WHEN** the user clicks Cancel or closes the modal
- **THEN** the confirmation input is cleared and the deletion is not performed
