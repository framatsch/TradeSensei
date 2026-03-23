## ADDED Requirements

### Requirement: List Corporate Actions
The system SHALL allow an authenticated user to retrieve a paginated list of all their Corporate Actions, ordered by date descending.

#### Scenario: User retrieves their corporate actions
- **WHEN** a `GET /api/v1/corporate-actions/` request is made with a valid JWT
- **THEN** the system SHALL return `200 OK` with a list of all Corporate Action records belonging to that user

#### Scenario: User has no corporate actions
- **WHEN** a `GET /api/v1/corporate-actions/` request is made and the user has no records
- **THEN** the system SHALL return `200 OK` with an empty list

---

### Requirement: Create Corporate Action
The system SHALL allow an authenticated user to create a new Corporate Action record specifying symbol, date, ratio, and optional old/new broker contract IDs.

#### Scenario: Successful creation of a reverse split
- **WHEN** a `POST /api/v1/corporate-actions/` request is made with `symbol="OTLK"`, `date="2024-03-01"`, `ratio="0.05"`, `old_conid="357194941"`, `new_conid="690184975"`
- **THEN** the system SHALL return `201 Created` with the created record including an assigned `id`

#### Scenario: Creation with invalid ratio (zero or negative)
- **WHEN** a `POST /api/v1/corporate-actions/` request is made with `ratio="0"` or a negative value
- **THEN** the system SHALL return `422 Unprocessable Entity`

#### Scenario: Creation with missing required fields
- **WHEN** a `POST /api/v1/corporate-actions/` request is made without `symbol` or `date` or `ratio`
- **THEN** the system SHALL return `422 Unprocessable Entity`

---

### Requirement: Update Corporate Action
The system SHALL allow an authenticated user to update an existing Corporate Action they own.

#### Scenario: Successful update
- **WHEN** a `PUT /api/v1/corporate-actions/{id}` request is made by the owning user with updated fields
- **THEN** the system SHALL return `200 OK` with the updated record

#### Scenario: Update of another user's Corporate Action
- **WHEN** a `PUT /api/v1/corporate-actions/{id}` request is made by a user who does not own the record
- **THEN** the system SHALL return `404 Not Found`

---

### Requirement: Delete Corporate Action
The system SHALL allow an authenticated user to delete a Corporate Action they own.

#### Scenario: Successful deletion
- **WHEN** a `DELETE /api/v1/corporate-actions/{id}` request is made by the owning user
- **THEN** the system SHALL return `204 No Content` and the record SHALL no longer exist

#### Scenario: Deletion of another user's Corporate Action
- **WHEN** a `DELETE /api/v1/corporate-actions/{id}` request is made by a non-owner
- **THEN** the system SHALL return `404 Not Found`

---

### Requirement: Corporate Action UI Management Page
The system SHALL provide a settings page in the frontend where the user can view, create, edit, and delete Corporate Actions without requiring technical knowledge of the underlying ratio value.

#### Scenario: User opens the Corporate Actions settings page
- **WHEN** the user navigates to the Corporate Actions settings page
- **THEN** the system SHALL display a table listing all existing Corporate Actions with columns: Symbol, Date, Split Ratio (human-readable, e.g. "1:20 Reverse Split"), Old Conid, New Conid

#### Scenario: User creates a split using a human-readable ratio input
- **WHEN** the user opens the "Add Corporate Action" form and enters "20" in "Before" and "1" in "After"
- **THEN** the frontend SHALL compute `ratio = after / before = 0.05` and submit that value to the API

#### Scenario: User deletes a corporate action
- **WHEN** the user clicks "Delete" on an existing Corporate Action record and confirms
- **THEN** the system SHALL call `DELETE /api/v1/corporate-actions/{id}` and remove the row from the table
