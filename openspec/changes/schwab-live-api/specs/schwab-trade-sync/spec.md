## ADDED Requirements

### Requirement: On-demand Schwab trade sync
The system SHALL provide a `POST /broker/schwab/sync` endpoint that fetches recent executed orders from the Schwab Orders API, normalizes them to the `Trade` model, and inserts deduplicated records into the journal.

The endpoint SHALL:
- Automatically refresh the Schwab access token if expired (using the stored refresh token)
- Fetch orders from the last 60 days by default (configurable via optional `days` query param, max 365)
- Normalize each filled equity/option order to a `TradeCreate` schema using `SchwabOrderNormalizer`
- Deduplicate using `broker_order_id` (Schwab's `orderId`) — skip trades already imported
- Return a summary: `{"imported_count": 5, "skipped_count": 12, "errors": []}`
- Update `last_sync_at` on the `broker_connections` record after successful sync

#### Scenario: Sync imports new trades
- **WHEN** an authenticated user with a connected Schwab account calls `POST /broker/schwab/sync`
- **THEN** new executed orders are fetched, normalized, and inserted; `imported_count` reflects the number of new trades

#### Scenario: Sync skips already-imported trades
- **WHEN** a trade with the same `broker_order_id` was already imported in a previous sync
- **THEN** that trade is skipped and counted in `skipped_count`

#### Scenario: Sync with expired access token refreshes automatically
- **WHEN** the stored access token is expired but the refresh token is valid
- **THEN** the system obtains a new access token, stores it, and proceeds with the sync

#### Scenario: Sync with expired refresh token returns 401
- **WHEN** both the access token and refresh token are expired
- **THEN** the API returns HTTP 401 with a message indicating reconnection is required

#### Scenario: Sync without a Schwab connection returns 404
- **WHEN** the authenticated user has no connected Schwab account
- **THEN** the API returns HTTP 404

#### Scenario: Unauthenticated sync request is rejected
- **WHEN** a request is made without a valid JWT
- **THEN** the API returns HTTP 401
