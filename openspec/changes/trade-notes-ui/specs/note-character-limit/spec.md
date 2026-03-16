## ADDED Requirements

### Requirement: Note content character limit
The system SHALL enforce a maximum of 5000 characters on trade note content at the API level.

The `TradeNoteCreate.content` and `TradeNoteUpdate.content` Pydantic fields SHALL have `max_length=5000`. The API SHALL return HTTP 422 with a descriptive validation error when the limit is exceeded.

#### Scenario: Note within limit is accepted
- **WHEN** a user creates or updates a note with content of 5000 characters or fewer
- **THEN** the API accepts the request and returns HTTP 201 or HTTP 200

#### Scenario: Note exceeding limit is rejected
- **WHEN** a user submits note content longer than 5000 characters
- **THEN** the API returns HTTP 422 with a validation error indicating the character limit

#### Scenario: Frontend shows character count approaching limit
- **WHEN** the note textarea contains 4500 or more characters
- **THEN** the character counter is displayed in a warning color to indicate the limit is near
