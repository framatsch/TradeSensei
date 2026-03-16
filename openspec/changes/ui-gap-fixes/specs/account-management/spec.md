## ADDED Requirements

### Requirement: Account management page exists
A new page at `/dashboard/accounts` SHALL be accessible from the sidebar navigation and SHALL list all accounts belonging to the current user.

#### Scenario: User navigates to accounts page
- **WHEN** user clicks "Accounts" in the sidebar
- **THEN** the `/dashboard/accounts` page loads and shows a list of the user's accounts

#### Scenario: Empty state
- **WHEN** the user has no accounts
- **THEN** a message "No accounts yet" is shown with a "Create account" button

### Requirement: User can create a new account
The accounts page SHALL include a "New Account" button that opens a form with fields: name (required), broker (required), currency (required, default USD), description (optional).

#### Scenario: Create account success
- **WHEN** user fills in the required fields and submits the create form
- **THEN** a POST request is sent to `/accounts`
- **AND** the new account appears in the list

#### Scenario: Create account with duplicate name
- **WHEN** user submits a name that already exists
- **THEN** the backend error is displayed inline on the name field

### Requirement: User can edit an existing account
Each account row SHALL have an "Edit" action that opens an inline or modal edit form.

#### Scenario: Edit account
- **WHEN** user clicks "Edit" on an account row and submits changes
- **THEN** a PATCH request is sent to `/accounts/{id}`
- **AND** the updated values are reflected in the list

### Requirement: User can delete an account
Each account row SHALL have a "Delete" action that requires confirmation before deletion.

#### Scenario: Delete account confirmed
- **WHEN** user clicks "Delete" on an account and confirms the dialog
- **THEN** a DELETE request is sent to `/accounts/{id}`
- **AND** the account is removed from the list

#### Scenario: Delete account cancelled
- **WHEN** user clicks "Delete" but cancels the dialog
- **THEN** no API call is made and the account remains in the list
