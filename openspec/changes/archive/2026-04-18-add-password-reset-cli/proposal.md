## Why

Administrators and developers need a quick, reliable way to reset user passwords from the command line without going through the web interface or writing manual SQL update queries. A CLI tool makes account recovery or testing safer and more convenient.

## What Changes

- Create a new backend CLI tool (`reset_password.py`) that can reset a user's password.
- The tool must look up the user either by their `username` or `email` address.
- ~~It must accept the new plaintext password via a command-line parameter.~~ **Superseded by `security-hardening`**: the `-p/--password` argument is intentionally omitted. Password is read interactively via `getpass.getpass()` or from stdin when piped — see `security-hardening` tasks 4.1–4.4.
- It must correctly securely hash the password using the project's existing cryptography methods.
- It should properly handle environment variables, database connectivity, and bcrypt/passlib incompatibilities within the project's current dependency tree.
- It must also increment the user's `refresh_token_version` to immediately invalidate their existing active sessions for security.

## Capabilities

### New Capabilities
- `password-reset-cli`: A backend command line utility to manually set a user's password and terminate their active sessions.

### Modified Capabilities
- 

## Impact

- **Backend**: A new file `backend/reset_password.py` will be created.
- **Dependencies**: No new dependencies, but uses existing `SQLAlchemy`, `pydantic-settings`, and `passlib`/`bcrypt`.
- **Database**: No schema changes, but directly updates the `hashed_password` and `refresh_token_version` fields in the `users` table.
