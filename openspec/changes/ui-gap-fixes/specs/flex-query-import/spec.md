## ADDED Requirements

### Requirement: Import page has a Flex Query tab
The `/dashboard/import` page SHALL have two tabs: "File Upload" (existing) and "Flex Query" (new). The Flex Query tab SHALL contain a form with fields for IBKR Query ID and IBKR Token.

#### Scenario: User navigates to Flex Query tab
- **WHEN** user clicks the "Flex Query" tab on the import page
- **THEN** the Flex Query form is displayed with fields for "Query ID" and "Token"
- **AND** the file upload form is hidden

### Requirement: User can trigger a Flex Query import
Submitting the Flex Query form SHALL POST to `/imports/flex` with the query ID, token, and selected account ID.

#### Scenario: Successful Flex Query import
- **WHEN** user fills in a valid Query ID, Token, selects an account, and clicks "Import"
- **THEN** a POST request is sent to `/imports/flex`
- **AND** on success, a result summary is shown (trades imported count)

#### Scenario: Flex Query import fails
- **WHEN** the backend returns an error (e.g., IBKR authentication failure or timeout)
- **THEN** an error message describing the failure is shown below the form
- **AND** the form remains filled so the user can correct and retry

#### Scenario: Account is required
- **WHEN** user clicks "Import" without selecting an account
- **THEN** a validation error is shown on the account selector field
- **AND** no API call is made
