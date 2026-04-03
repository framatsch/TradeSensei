## ADDED Requirements

### Requirement: Manage cash transactions via API
The system SHALL provide CRUD endpoints to manage cash transaction records, including reading a paginated and filtered list of transactions.

#### Scenario: List cash transactions
- **WHEN** a user requests the list of cash transactions for an account
- **THEN** the system returns a paginated list of cash transactions sorted by date descending

#### Scenario: Filter cash transactions by type
- **WHEN** a user requests the list of cash transactions for an account with a `type` query parameter (e.g., `DIVIDEND`)
- **THEN** the system returns only the transactions matching that type

#### Scenario: Create manual cash transaction
- **WHEN** a user submits a valid payload to create a new cash transaction
- **THEN** the system saves the transaction and returns the created record with its assigned UUID

#### Scenario: Delete cash transaction
- **WHEN** a user requests to delete a specific cash transaction by ID
- **THEN** the system removes the record and returns a success response