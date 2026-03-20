## MODIFIED Requirements

### Requirement: token_expires_at is optional on BrokerConnection
The `BrokerConnection` model and table SHALL allow `token_expires_at` to be `NULL`. This is required to accommodate non-OAuth brokers (e.g. IBKR Flex) where there is no short-lived token expiry managed by the system. All existing code paths that read `token_expires_at` for Schwab SHALL guard against `None` before comparison. New connections for Schwab SHALL continue to set `token_expires_at` to the actual expiry timestamp from the OAuth response.

#### Scenario: Schwab connection retains token expiry
- **WHEN** a Schwab OAuth connection is saved
- **THEN** `token_expires_at` is set to the expiry timestamp from the OAuth token response

#### Scenario: IBKR connection has no token expiry
- **WHEN** an IBKR Flex connection is saved via `POST /broker/ibkr/connect`
- **THEN** `token_expires_at` is stored as `NULL` in the database
- **AND** the existing Schwab token-refresh logic does NOT process this row

#### Scenario: Token refresh skips IBKR rows
- **WHEN** the background token refresh process runs
- **THEN** it only processes `BrokerConnection` rows where `broker != "ibkr"` OR where `token_expires_at IS NOT NULL`
- **AND** IBKR rows are never erroneously refreshed
