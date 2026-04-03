## ADDED Requirements

### Requirement: Schwab OAuth connect flow
The system SHALL provide a `GET /broker/schwab/connect` endpoint that redirects the authenticated user to Schwab's OAuth 2.0 authorization page with PKCE. A `state` parameter SHALL be generated and stored server-side to prevent CSRF.

#### Scenario: Connect redirects to Schwab authorization
- **WHEN** an authenticated user calls `GET /broker/schwab/connect`
- **THEN** the response is an HTTP 302 redirect to Schwab's authorization URL with `client_id`, `redirect_uri`, `state`, `code_challenge`, and `scope` query parameters

#### Scenario: Unauthenticated connect is rejected
- **WHEN** a request is made without a valid JWT
- **THEN** the API returns HTTP 401

### Requirement: Schwab OAuth callback
The system SHALL provide a `GET /broker/schwab/callback` endpoint that handles the OAuth callback from Schwab, exchanges the authorization code for tokens, encrypts and stores the tokens in `broker_connections`, and redirects to the frontend connections page.

#### Scenario: Successful callback stores tokens
- **WHEN** Schwab redirects to the callback URL with a valid `code` and matching `state`
- **THEN** the backend exchanges the code for access and refresh tokens, stores them encrypted in `broker_connections`, and redirects to `/dashboard/connections?connected=schwab`

#### Scenario: Invalid state returns 400
- **WHEN** the callback is received with a `state` that does not match the stored state
- **THEN** the API returns HTTP 400 with an error message

### Requirement: Schwab disconnect
The system SHALL provide a `DELETE /broker/schwab/disconnect` endpoint that revokes the stored Schwab tokens and deletes the `broker_connections` record for the authenticated user.

#### Scenario: Disconnect removes stored tokens
- **WHEN** an authenticated user calls `DELETE /broker/schwab/disconnect`
- **THEN** the Schwab connection record is deleted and the user is no longer connected

#### Scenario: Disconnect with no connection returns 404
- **WHEN** the user has no existing Schwab connection and calls disconnect
- **THEN** the API returns HTTP 404

### Requirement: Schwab connection status
The system SHALL provide a `GET /broker/schwab/status` endpoint that returns whether the authenticated user has a connected Schwab account and the timestamp of the last successful sync.

#### Scenario: Returns connected status and last sync time
- **WHEN** an authenticated user calls `GET /broker/schwab/status` and has a Schwab connection
- **THEN** the response contains `{"connected": true, "last_sync_at": "2025-11-14T10:00:00Z"}`

#### Scenario: Returns disconnected status
- **WHEN** an authenticated user calls `GET /broker/schwab/status` and has no Schwab connection
- **THEN** the response contains `{"connected": false, "last_sync_at": null}`
