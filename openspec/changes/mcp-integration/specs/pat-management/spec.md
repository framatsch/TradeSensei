## ADDED Requirements

### Requirement: Personal Access Token Model
The system SHALL store PATs in the database with a reference to the owning user, a name, a SHA-256 hash of the token, creation date, optional expiration date, a revocation flag, and a `last_used_at` timestamp.

#### Scenario: Token creation records correctly
- **WHEN** a new PAT is created
- **THEN** the system generates a secure token string, stores its SHA-256 hash in the database, sets `last_used_at` to null, and returns the plaintext token exactly once

### Requirement: Token Listing Endpoint
The system SHALL provide a GET endpoint at `/api/v1/settings/tokens` to list a user's PATs.

#### Scenario: List active tokens
- **WHEN** a user views their settings
- **THEN** the API returns a list of their tokens including ID, name, expiration, revocation status, and `last_used_at`, but NOT the token hash or value

### Requirement: Token Generation Endpoint
The system SHALL provide a POST endpoint at `/api/v1/settings/tokens` to generate a new PAT. It MUST return the plaintext token exactly once.

#### Scenario: Successful token generation
- **WHEN** a user requests to generate a new PAT with a name and expiration
- **THEN** the API returns the plaintext token and token metadata

### Requirement: Token Revocation Endpoint
The system SHALL provide a DELETE endpoint at `/api/v1/settings/tokens/{id}` to revoke a PAT.

#### Scenario: Revoke a token
- **WHEN** a user revokes an active PAT
- **THEN** the token's `is_revoked` flag is set to `true` and it can no longer be used for authentication

### Requirement: Token Management UI
The system SHALL provide a user interface in the Settings view to generate, list, and revoke PATs.

#### Scenario: Generate token in UI
- **WHEN** a user clicks "Generate New Token", fills the form, and submits
- **THEN** a modal displays the generated plaintext token with a "Copy" button, warning that it will not be shown again

#### Scenario: View token list in UI
- **WHEN** a user navigates to the "API & Tokens" settings page
- **THEN** they see a table of their active and revoked tokens with `last_used_at` shown, and options to revoke active ones