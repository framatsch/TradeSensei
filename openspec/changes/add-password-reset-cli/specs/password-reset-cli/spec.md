## ADDED Requirements

### Requirement: Admin can reset password via CLI
The system SHALL provide a CLI utility to reset a user's password directly in the database without requiring authentication.

#### Scenario: Reset via username
- **WHEN** the CLI tool is executed with `-u <username>` and `-p <new_password>`
- **THEN** the system MUST hash the password, update the `users` table, increment `refresh_token_version`, and print a success message.

#### Scenario: Reset via email
- **WHEN** the CLI tool is executed with `-e <email>` and `-p <new_password>`
- **THEN** the system MUST look up the user by email, update their password and token version, and print a success message.

#### Scenario: User not found
- **WHEN** the given username or email does not exist in the database
- **THEN** the system MUST print an error message and exit with code 1.

#### Scenario: Missing required environment variables
- **WHEN** the system lacks `SECRET_KEY` or `DATABASE_URL` (and `DB_USER`)
- **THEN** the script MUST use safe fallbacks to prevent `pydantic-settings` from crashing and provide a helpful warning message or exit gracefully if database connection fails.
