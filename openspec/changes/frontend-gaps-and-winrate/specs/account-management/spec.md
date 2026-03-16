## ADDED Requirements

### Requirement: User can view their broker accounts
The system SHALL display a list of all broker accounts belonging to the
authenticated user, showing name, broker, currency, and active status.

#### Scenario: Account list loads
- **WHEN** user navigates to `/dashboard/accounts`
- **THEN** the page displays all accounts with name, broker, currency, and active status
- **AND** a "New Account" button is visible

#### Scenario: Empty state
- **WHEN** user has no accounts
- **THEN** the page displays an empty state message with a prompt to create the first account

---

### Requirement: User can create a broker account
The system SHALL provide a form for creating a new broker account with name
(required), broker (optional), currency (default USD), and active flag.

#### Scenario: Successful creation
- **WHEN** user fills in a valid name and submits the create form
- **THEN** the new account appears in the list
- **AND** the form closes/resets

#### Scenario: Duplicate name rejected
- **WHEN** user submits a name that already exists for their user
- **THEN** the form displays an error "Account name already exists"
- **AND** the account is not created

---

### Requirement: User can edit a broker account
The system SHALL allow the user to edit name, broker, currency, and active status
of an existing account.

#### Scenario: Successful edit
- **WHEN** user clicks "Edit" on an account and submits valid changes
- **THEN** the account list reflects the updated values

---

### Requirement: User can delete a broker account
The system SHALL allow the user to delete an account, with a confirmation dialog
warning that all associated trades will also be deleted.

#### Scenario: Delete with confirmation
- **WHEN** user clicks "Delete" and confirms the dialog
- **THEN** the account is removed from the list
- **AND** associated trades are no longer accessible

#### Scenario: Cancel delete
- **WHEN** user clicks "Delete" but cancels the confirmation dialog
- **THEN** the account remains unchanged

---

### Requirement: Accounts page is accessible from navigation
The system SHALL include "Accounts" as a navigation item in the dashboard sidebar.

#### Scenario: Navigation link present
- **WHEN** user is on any dashboard page
- **THEN** the sidebar contains an "Accounts" link that navigates to `/dashboard/accounts`
