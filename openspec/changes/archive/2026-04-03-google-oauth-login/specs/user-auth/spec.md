## MODIFIED Requirements

### Requirement: User password is optional for OAuth accounts
The `hashed_password` column on the `users` table SHALL be nullable. Users authenticated via Google OAuth SHALL have `hashed_password = NULL`. Password-based login SHALL be rejected for users with `hashed_password = NULL`.

#### Scenario: Google user cannot log in with password
- **WHEN** a POST to `/api/v1/auth/token` is made with credentials belonging to a user whose `provider = 'google'`
- **THEN** the server responds with HTTP 401 and error `oauth_account_no_password`

#### Scenario: Local user login unchanged
- **WHEN** a POST to `/api/v1/auth/token` is made with valid credentials for a user with `provider = 'local'`
- **THEN** the server responds with HTTP 200 and a `TokenResponse` as before

## ADDED Requirements

### Requirement: User provider tracking
The `users` table SHALL include a `provider` column (`VARCHAR(20)`, NOT NULL, default `'local'`) and a `provider_id` column (`VARCHAR(255)`, nullable). A unique constraint SHALL exist on `(provider, provider_id)` where `provider_id IS NOT NULL`.

#### Scenario: Existing users have provider = local
- **WHEN** the migration runs on a database with existing users
- **THEN** all existing rows have `provider = 'local'` and `provider_id = NULL`
