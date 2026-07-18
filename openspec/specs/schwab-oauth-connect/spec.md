## ADDED Requirements

### Requirement: Start Schwab OAuth Authorization
The system SHALL let an authenticated user begin a Schwab OAuth authorization for a specific account by generating a PKCE code verifier and a CSRF `state`, persisting the verifier, the `state`, and a `state → account_id` correlation server-side for short-lived lookup, and returning the Schwab authorization URL built from the account's app credentials and the configured `schwab_redirect_uri`.

The endpoint SHALL require a valid Bearer token, SHALL be scoped to the authenticated user's own account, and SHALL use the account's per-account `SCHWAB_APP_KEY`/`SCHWAB_APP_SECRET` properties (consistent with IBKR credential storage) as the OAuth `client_id`/`client_secret`, and the central `schwab_redirect_uri` setting (default `https://127.0.0.1`) as the `redirect_uri`. It SHALL fail with a configuration error when the account has no stored `SCHWAB_APP_KEY`/`SCHWAB_APP_SECRET`.

#### Scenario: User requests an authorization URL for their account
- **WHEN** an authenticated user requests to connect a Schwab account they own
- **THEN** the system SHALL generate a PKCE code verifier and a random `state`
- **THEN** the system SHALL persist the verifier, the `state`, and a `state → account_id` correlation for later lookup
- **THEN** the system SHALL return an authorization URL containing `client_id`, the configured `redirect_uri`, `code_challenge`, `code_challenge_method=S256`, and the generated `state`

#### Scenario: Authorization requested for an account owned by another user
- **WHEN** an authenticated user requests to connect a Schwab account that belongs to a different user
- **THEN** the system SHALL respond with HTTP 404 to avoid account-ID enumeration

#### Scenario: Schwab application credentials are not configured
- **WHEN** a user requests an authorization URL for an account that has no stored `SCHWAB_APP_KEY`/`SCHWAB_APP_SECRET` properties
- **THEN** the system SHALL respond with HTTP 400 indicating the account's Schwab app credentials must be set first

#### Scenario: Redirect URI is taken from the central setting
- **WHEN** the system builds the authorization URL
- **THEN** it SHALL use the `schwab_redirect_uri` setting (default `https://127.0.0.1`) as the `redirect_uri`, and this SHALL match the value used later during code exchange

### Requirement: OAuth Mode and Redirect URI Consistency
The system SHALL support two OAuth completion modes selected by the `schwab_oauth_mode` setting: `paste` (the user pastes the redirect URL) and `callback` (Schwab redirects the browser to a server endpoint). At authorization time the system SHALL validate that the mode and the configured `schwab_redirect_uri` are consistent.

#### Scenario: Callback mode configured with a loopback redirect URI
- **WHEN** `schwab_oauth_mode` is `callback` and `schwab_redirect_uri` points at a loopback host (`127.0.0.1` or `localhost`)
- **THEN** the system SHALL reject the authorization start with HTTP 400 indicating callback mode requires a non-loopback, TLS-terminated redirect URI

#### Scenario: Paste mode uses a loopback redirect URI
- **WHEN** `schwab_oauth_mode` is `paste` and `schwab_redirect_uri` is `https://127.0.0.1`
- **THEN** the system SHALL build the authorization URL normally and expect completion via the paste endpoint

### Requirement: Complete Schwab Connection by Automatic Callback
When `schwab_oauth_mode` is `callback`, the system SHALL expose an unauthenticated `GET` callback endpoint that Schwab redirects to with `code` and `state`. The endpoint SHALL resolve the target account by looking up the `state → account_id` correlation persisted at authorization time (no Bearer token is present on this browser redirect), validate the `state`, exchange the `code` for tokens using the resolved account's app credentials and the same `redirect_uri`, store the tokens, and redirect the browser back to the account settings page with a success or error indication.

The callback SHALL never expose token values in the URL, response body, or logs. It SHALL only act on a `state` that matches a stored correlation.

#### Scenario: Valid callback completes the connection automatically
- **WHEN** Schwab redirects to the callback endpoint with a `code` and a `state` that matches a stored `state → account_id` correlation
- **THEN** the system SHALL resolve the account from the `state`, exchange the `code` for tokens using that account's `SCHWAB_APP_KEY`/`SCHWAB_APP_SECRET` and the configured `redirect_uri`
- **THEN** the system SHALL persist the encrypted token properties and clear the one-time verifier/state/correlation records
- **THEN** the system SHALL emit a `broker.schwab_connected` audit event with only safe identifiers
- **THEN** the system SHALL redirect the browser to the account settings page indicating success

#### Scenario: Callback with an unknown or expired state
- **WHEN** the callback receives a `state` that does not match any stored correlation
- **THEN** the system SHALL NOT exchange the code and SHALL redirect to the settings page indicating the authorization could not be matched (or expired)

#### Scenario: Callback missing the authorization code
- **WHEN** the callback is invoked without a `code` parameter (e.g. the user denied consent)
- **THEN** the system SHALL NOT persist tokens and SHALL redirect to the settings page indicating the connection was not completed

#### Scenario: Token exchange fails during callback
- **WHEN** the Schwab token endpoint returns a non-success response during a callback exchange
- **THEN** the system SHALL NOT persist partial tokens and SHALL redirect to the settings page indicating the connection failed

### Requirement: Complete Schwab Connection by Pasted Redirect URL
When `schwab_oauth_mode` is `paste`, the system SHALL let an authenticated user complete a Schwab connection by pasting the full redirect URL captured from the browser address bar. The system SHALL extract the `code` and `state` query parameters, validate the `state` against the previously persisted value for that account, exchange the `code` for tokens via the PKCE `code_verifier`, and store the resulting tokens. This endpoint is Bearer-authenticated and scoped to the authenticated user's own account.

Tokens SHALL be stored as Fernet-encrypted `AccountProperty` rows on the account using the keys `SCHWAB_ACCESS_TOKEN`, `SCHWAB_REFRESH_TOKEN`, and `SCHWAB_TOKEN_EXPIRES_AT`, consistent with how IBKR credentials are stored. Raw tokens SHALL never be logged or returned in responses.

#### Scenario: Valid redirect URL completes the connection
- **WHEN** the user pastes a redirect URL of the form `https://127.0.0.1/?code=<code>&state=<state>` whose `state` matches the persisted value
- **THEN** the system SHALL exchange the `code` for an access token, refresh token, and expiry using the stored `code_verifier`, the account's `SCHWAB_APP_KEY`/`SCHWAB_APP_SECRET`, and the same `schwab_redirect_uri` used to build the authorization URL
- **THEN** the system SHALL persist the three token properties encrypted on the account
- **THEN** the system SHALL clear the one-time `code_verifier`/`state` correlation record
- **THEN** the system SHALL emit a `broker.schwab_connected` audit event containing only safe identifiers (no token values)

#### Scenario: Redirect URL is missing the authorization code
- **WHEN** the pasted URL does not contain a `code` query parameter
- **THEN** the system SHALL respond with HTTP 400 indicating the redirect URL is missing the authorization code

#### Scenario: State parameter does not match
- **WHEN** the pasted URL's `state` does not match the persisted value for the account
- **THEN** the system SHALL reject the request with HTTP 400 and SHALL NOT exchange the code

#### Scenario: Token exchange fails at Schwab
- **WHEN** the Schwab token endpoint returns a non-success response during code exchange
- **THEN** the system SHALL respond with HTTP 400 indicating the connection could not be completed and SHALL NOT persist partial tokens

### Requirement: Schwab Connection Status and Disconnect
The system SHALL report whether an account has a stored Schwab access/refresh token and SHALL allow an authenticated user to disconnect by deleting the stored token properties. Status responses SHALL NOT include token values.

#### Scenario: Account has stored tokens
- **WHEN** an authenticated user queries the Schwab connection status for an account that has `SCHWAB_ACCESS_TOKEN` and `SCHWAB_REFRESH_TOKEN` stored
- **THEN** the system SHALL report the account as connected without revealing token values

#### Scenario: User disconnects a Schwab account
- **WHEN** an authenticated user disconnects Schwab for an account they own
- **THEN** the system SHALL delete the `SCHWAB_ACCESS_TOKEN`, `SCHWAB_REFRESH_TOKEN`, and `SCHWAB_TOKEN_EXPIRES_AT` properties
- **THEN** the system SHALL emit a `broker.schwab_disconnected` audit event with only safe identifiers

### Requirement: Transparent Access-Token Refresh
The system SHALL refresh an expired or soon-to-expire Schwab access token using the stored refresh token before making broker API calls, and SHALL persist the rotated access token and expiry. Schwab access tokens are valid for 30 minutes; refresh tokens have a hard 7-day lifetime from creation and cannot be extended.

#### Scenario: Access token expired at sync time
- **WHEN** a broker operation needs the Schwab access token and the stored `SCHWAB_TOKEN_EXPIRES_AT` is in the past or within the refresh threshold
- **THEN** the system SHALL call the Schwab token endpoint with the stored refresh token
- **THEN** the system SHALL persist the new access token and expiry (and refresh token if rotated) before proceeding

#### Scenario: Refresh token is invalid or expired
- **WHEN** the refresh call fails because the refresh token is no longer valid (e.g. the 7-day limit has elapsed, yielding `invalid_client`)
- **THEN** the system SHALL surface an actionable "reconnect required" error rather than a generic failure

### Requirement: Schwab Test Connection
The system SHALL provide a Schwab test-connection that verifies live API connectivity by fetching account numbers with a valid access token. The Schwab Trader API has no ping endpoint; the lightest authenticated read (`get_account_numbers`) is used. A test SHALL only perform a network call when the account is already connected via OAuth.

#### Scenario: Test connection on a connected account
- **WHEN** a test connection is requested for a Schwab account that has stored access/refresh tokens
- **THEN** the system SHALL obtain a valid access token (refreshing if needed) and call the Schwab accounts endpoint
- **THEN** the system SHALL report success when the call returns account data, using the access token (not the App Key) as the Bearer credential

#### Scenario: Test connection before the account is connected
- **WHEN** a test connection is requested for a Schwab account that has no stored access/refresh tokens
- **THEN** the system SHALL return an HTTP 400 indicating the account must be connected via the Schwab OAuth flow first, without making a network call
