## ADDED Requirements

### Requirement: Forgot-password request endpoint
The backend SHALL expose `POST /api/v1/auth/forgot-password` accepting `{"email": "<address>"}`. It SHALL always return HTTP 200 with the message `"If an account with that email exists, a reset link has been sent."` regardless of whether the email is registered, to prevent user enumeration. An email with a reset link SHALL be sent only when: a user with that email exists AND `hashed_password IS NOT NULL` AND SMTP is configured.

#### Scenario: Known local-auth user
- **WHEN** `POST /auth/forgot-password` is called with an email belonging to a user with a local password
- **THEN** HTTP 200 is returned and a reset email is sent to that address

#### Scenario: Unknown email
- **WHEN** `POST /auth/forgot-password` is called with an email that is not registered
- **THEN** HTTP 200 is returned and no email is sent

#### Scenario: OAuth-only user (no local password)
- **WHEN** `POST /auth/forgot-password` is called with an email belonging to a user whose `hashed_password` is NULL
- **THEN** HTTP 200 is returned and no email is sent

#### Scenario: SMTP not configured
- **WHEN** `POST /auth/forgot-password` is called but SMTP settings are missing
- **THEN** HTTP 503 is returned with detail "Password reset is not configured."

---

### Requirement: Password reset token
The backend SHALL generate a signed JWT with claim `"pwreset": true`, a unique `jti`, and a 1-hour expiry. The token SHALL be embedded in the reset link as a query parameter: `{FRONTEND_URL}/reset-password?token=<jwt>`. After use the `jti` SHALL be recorded in `used_otts` so the token cannot be replayed.

#### Scenario: Token is single-use
- **WHEN** `POST /auth/reset-password` is called with a valid token
- **THEN** the `jti` is inserted into `used_otts` and any subsequent use of the same token returns HTTP 401

#### Scenario: Token expires after 1 hour
- **WHEN** `POST /auth/reset-password` is called with a token older than 1 hour
- **THEN** HTTP 401 is returned with detail "Reset link has expired."

---

### Requirement: Reset-password endpoint
The backend SHALL expose `POST /api/v1/auth/reset-password` accepting `{"token": "<jwt>", "new_password": "<plain>"}`. On success it SHALL hash the new password, update `hashed_password`, increment `refresh_token_version` (invalidating all active sessions), and return HTTP 200.

#### Scenario: Valid token and strong password
- **WHEN** `POST /auth/reset-password` is called with a valid unexpired token and a password ≥ 8 characters
- **THEN** HTTP 200 is returned, the password is updated, and all existing sessions are invalidated

#### Scenario: Invalid or tampered token
- **WHEN** `POST /auth/reset-password` is called with a malformed or tampered token
- **THEN** HTTP 401 is returned

#### Scenario: Password too short
- **WHEN** `POST /auth/reset-password` is called with a `new_password` shorter than 8 characters
- **THEN** HTTP 422 is returned

---

### Requirement: Forgot-password page
The frontend SHALL provide a `/forgot-password` page with a single email input and a submit button. After submission it SHALL display a static success message regardless of the server response, to avoid leaking whether the email is registered.

#### Scenario: Success state
- **WHEN** the user submits a valid email address
- **THEN** the form is replaced with "If an account exists for that email, you'll receive a reset link shortly."

#### Scenario: Link back to login
- **WHEN** the forgot-password page is displayed
- **THEN** a "Back to login" link is visible

---

### Requirement: Reset-password page
The frontend SHALL provide a `/reset-password` page that reads the `token` query parameter. If the token is absent it SHALL redirect to `/forgot-password`. The page SHALL show a new-password form with a confirmation field. On success it SHALL redirect to `/login` with a success notice.

#### Scenario: Missing token in URL
- **WHEN** the user visits `/reset-password` without a `?token=` parameter
- **THEN** the page redirects to `/forgot-password`

#### Scenario: Successful reset
- **WHEN** the user submits matching passwords and the token is valid
- **THEN** the password is updated and the user is redirected to `/login?reset=success`

#### Scenario: Expired or used token
- **WHEN** the backend returns 401 on the reset attempt
- **THEN** an error message is shown: "This reset link has expired or has already been used." with a link to request a new one

#### Scenario: Password mismatch
- **WHEN** the user submits passwords that do not match
- **THEN** an inline validation error is shown before the form is submitted

---

### Requirement: Forgot-password link on login page
The frontend login page SHALL render a "Forgot password?" link below the password field only when the auth config returns `password_reset_enabled: true`.

#### Scenario: Link shown when reset is enabled
- **WHEN** `GET /auth/config` returns `password_reset_enabled: true`
- **THEN** the login page shows a "Forgot password?" link pointing to `/forgot-password`

#### Scenario: Link hidden when reset is disabled
- **WHEN** `GET /auth/config` returns `password_reset_enabled: false`
- **THEN** no "Forgot password?" link is rendered on the login page
