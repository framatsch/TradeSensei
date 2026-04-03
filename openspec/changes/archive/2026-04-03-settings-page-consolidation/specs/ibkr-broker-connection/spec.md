## ADDED Requirements

### Requirement: IBKR Flex credentials can be saved via API
The system SHALL expose `POST /broker/ibkr/connect` accepting `{ "flex_query_id": string, "flex_token": string }`. Both values SHALL be encrypted using Fernet before storage in `broker_connections` with `broker="ibkr"`. If a connection for this user already exists it SHALL be overwritten (upsert). The endpoint SHALL require JWT authentication.

Mapping to `BrokerConnection` columns:
- `broker` = `"ibkr"`
- `access_token` = encrypted `flex_token`
- `refresh_token` = encrypted `flex_query_id`
- `token_expires_at` = `NULL` (IBKR tokens do not have short-lived expiry)

#### Scenario: First-time IBKR connect
- **WHEN** an authenticated user calls `POST /broker/ibkr/connect` with valid `flex_query_id` and `flex_token`
- **THEN** the response is `200 OK` with `{ "connected": true, "last_sync_at": null }`
- **AND** a `BrokerConnection` row with `broker="ibkr"` exists for the user

#### Scenario: Update existing IBKR credentials
- **WHEN** an authenticated user already has an IBKR connection and calls `POST /broker/ibkr/connect` with new credentials
- **THEN** the response is `200 OK` and the existing row is updated with the new encrypted credentials

#### Scenario: Empty credentials are rejected
- **WHEN** an authenticated user calls `POST /broker/ibkr/connect` with an empty string for `flex_token`
- **THEN** the response is `422 Unprocessable Entity`

### Requirement: IBKR connection status can be queried
The system SHALL return IBKR connection status via the existing `GET /broker/ibkr/status` endpoint pattern (generic broker status endpoint), returning `{ "connected": bool, "last_sync_at": datetime | null }`.

#### Scenario: Status when connected
- **WHEN** an authenticated user has a saved IBKR connection
- **AND** calls `GET /broker/ibkr/status`
- **THEN** the response is `200 OK` with `{ "connected": true, "last_sync_at": <value or null> }`

#### Scenario: Status when not connected
- **WHEN** an authenticated user has no IBKR connection
- **AND** calls `GET /broker/ibkr/status`
- **THEN** the response is `200 OK` with `{ "connected": false, "last_sync_at": null }`

### Requirement: IBKR connection can be removed
The system SHALL allow disconnecting IBKR via the existing `DELETE /broker/ibkr` endpoint pattern, deleting the `BrokerConnection` row for `broker="ibkr"`.

#### Scenario: Disconnect IBKR
- **WHEN** an authenticated user has a saved IBKR connection
- **AND** calls `DELETE /broker/ibkr`
- **THEN** the response is `200 OK`
- **AND** subsequent `GET /broker/ibkr/status` returns `{ "connected": false }`

### Requirement: IBKR connection card shown in Settings UI
The frontend SHALL display an IBKR card in the Accounts & Integrations tab. When disconnected, it SHALL show a form with inputs for "Flex Query ID" and "Flex Token" and a "Connect" button. When connected, it SHALL show a connected status indicator, the last sync timestamp (if any), and a "Disconnect" button.

#### Scenario: Display connect form when not connected
- **WHEN** the user opens Settings → Accounts & Integrations
- **AND** no IBKR connection exists
- **THEN** the IBKR card shows input fields for Flex Query ID and Flex Token
- **AND** a "Connect" submit button is visible

#### Scenario: Display connected state
- **WHEN** the user opens Settings → Accounts & Integrations
- **AND** an IBKR connection exists
- **THEN** the IBKR card shows "Connected" status with a "Disconnect" button
- **AND** credentials are NOT displayed in plaintext
