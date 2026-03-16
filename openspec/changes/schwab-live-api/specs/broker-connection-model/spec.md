## ADDED Requirements

### Requirement: Broker connection persistence
The system SHALL store OAuth broker connection credentials in a `broker_connections` table with the following columns: `id` (UUID PK), `user_id` (FK to users), `broker` (string enum: `schwab`), `access_token` (text, encrypted), `refresh_token` (text, encrypted), `token_expires_at` (timestamp), `last_sync_at` (timestamp nullable), `created_at`, `updated_at`.

The system SHALL encrypt `access_token` and `refresh_token` at rest using Fernet symmetric encryption with a key from the `BROKER_ENCRYPTION_KEY` environment variable.

There SHALL be at most one `broker_connections` record per `(user_id, broker)` pair (unique constraint).

#### Scenario: Connection record is created on successful OAuth callback
- **WHEN** a user completes the OAuth flow successfully
- **THEN** a `broker_connections` record is created with encrypted tokens and `last_sync_at = null`

#### Scenario: Reconnecting replaces existing connection
- **WHEN** a user with an existing Schwab connection completes the OAuth flow again
- **THEN** the existing record is updated (upsert) with the new tokens rather than creating a duplicate

#### Scenario: Missing BROKER_ENCRYPTION_KEY causes startup error
- **WHEN** the backend starts without `BROKER_ENCRYPTION_KEY` configured
- **THEN** the application fails to start with a clear configuration error
