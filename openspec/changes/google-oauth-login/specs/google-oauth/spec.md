## ADDED Requirements

### Requirement: Google OAuth initiation
The system SHALL provide a `GET /api/v1/auth/google` endpoint that redirects the browser to Google's OAuth 2.0 authorization URL with the correct `client_id`, `redirect_uri`, `scope` (`openid email profile`), `state`, and `response_type=code` parameters.

#### Scenario: Redirect to Google
- **WHEN** an unauthenticated user navigates to `GET /api/v1/auth/google`
- **THEN** the server responds with HTTP 302 and a `Location` header pointing to `accounts.google.com/o/oauth2/auth`

### Requirement: Google OAuth callback
The system SHALL provide a `GET /api/v1/auth/google/callback` endpoint that receives the authorization `code` from Google, exchanges it for an ID token, validates the ID token, and issues a JWT access token and refresh token identical to the password login flow.

#### Scenario: Valid callback issues JWT
- **WHEN** Google redirects to `/api/v1/auth/google/callback?code=<valid_code>&state=<valid_state>`
- **THEN** the server validates the code, retrieves the Google user profile, creates or retrieves the local user, sets the `httpOnly` refresh token cookie, and redirects the browser to the frontend callback page with a short-lived one-time token in the query string

#### Scenario: Invalid or replayed state
- **WHEN** the `state` parameter does not match the session state
- **THEN** the server responds with HTTP 400 and an error message `invalid_state`

#### Scenario: Email not verified by Google
- **WHEN** Google's ID token contains `email_verified: false`
- **THEN** the server responds with HTTP 400 and an error message `email_not_verified`

#### Scenario: Google returns error
- **WHEN** Google redirects with `?error=access_denied` (user cancelled)
- **THEN** the server redirects the browser to the frontend login page with `?error=oauth_cancelled`

### Requirement: Google user auto-provisioning
The system SHALL create a new user account automatically on the first successful Google login. The account SHALL have `provider = 'google'` and `provider_id` set to the Google `sub` claim. `hashed_password` SHALL be `NULL`.

#### Scenario: New Google user created
- **WHEN** a callback is received for a Google account whose `sub` does not exist in the database
- **THEN** a new `users` row is created with `provider='google'`, `provider_id=<sub>`, `email=<google_email>`, `username=<derived>`, `hashed_password=NULL`, `is_active=true`

#### Scenario: Username collision on provisioning
- **WHEN** the derived username (from Google display name) already exists
- **THEN** a numeric suffix is appended to ensure uniqueness (e.g., `johndoe2`)

### Requirement: Email-based account linking
The system SHALL link a Google login to an existing local account if the Google-provided email matches an existing user's email, regardless of their current `provider`.

#### Scenario: Existing local user with matching email
- **WHEN** a Google callback is received and a user with `email = <google_email>` already exists with `provider = 'local'`
- **THEN** the existing user's `provider` is updated to `'google'` and `provider_id` is set to the Google `sub`; no duplicate user is created

### Requirement: One-time token exchange
The system SHALL accept a `POST /api/v1/auth/google/exchange` request with a valid one-time token and respond with a full `TokenResponse` (access token + expiry). The one-time token SHALL expire after 60 seconds and be invalidated immediately upon use.

#### Scenario: Valid one-time token exchange
- **WHEN** the frontend posts a valid, unexpired one-time token to `/api/v1/auth/google/exchange`
- **THEN** the server responds with HTTP 200 and a `TokenResponse` containing the access token

#### Scenario: Expired one-time token
- **WHEN** the frontend posts a one-time token that is older than 60 seconds
- **THEN** the server responds with HTTP 401

#### Scenario: Already-used one-time token
- **WHEN** the frontend posts a one-time token that has already been exchanged
- **THEN** the server responds with HTTP 401
