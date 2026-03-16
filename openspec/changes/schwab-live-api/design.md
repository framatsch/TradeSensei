## Context

The project already implements a Schwab CSV file parser (`SchwabImportService`) and a similar IBKR Flex Query client (`fles/flex_client.py`). The existing import infrastructure (`ImportService`, `TradeRepository`) handles deduplication and insertion. Google OAuth is already implemented using `authlib`, which can also handle Schwab's standard OAuth 2.0 flow.

The Schwab Individual Trader API is a documented REST API (developer.schwab.com) that provides `GET /trader/v1/orders` for fetching executed orders. It uses standard OAuth 2.0 Authorization Code flow with PKCE.

## Goals / Non-Goals

**Goals:**
- Implement the complete OAuth 2.0 connect/callback/disconnect lifecycle for Schwab
- Store access + refresh tokens encrypted at rest in a `broker_connections` table
- Implement a `POST /broker/schwab/sync` endpoint that fetches orders from Schwab, normalizes them to the `Trade` model, and inserts deduplicated records
- Frontend "Connections" page to manage the Schwab integration status
- Automatic token refresh on sync if the access token is expired

**Non-Goals:**
- Real-time streaming of Schwab data (WebSocket / Streamer API)
- Support for multiple simultaneous Schwab accounts under one user
- IBKR TWS live connection (separate feature, Iteration 7 stretch)
- Scheduled automatic sync (cron/background tasks) — this change is on-demand only
- Supporting other brokers via this same connection infrastructure (future work)

## Decisions

### Token storage: encrypted DB column vs secrets manager

**Decision**: Store encrypted tokens in the `broker_connections` DB table using `cryptography.fernet` symmetric encryption with a `BROKER_ENCRYPTION_KEY` env var.

**Rationale**: Secrets managers (AWS Secrets Manager, Vault) add infrastructure complexity not justified for a self-hosted journal. Fernet encryption is battle-tested, simple to implement, and the key can be rotated. The trade-off is that the key must be carefully managed — document this clearly.

### OAuth library: authlib vs httpx manually

**Decision**: Reuse `authlib` (already a dependency from Google OAuth) for the Schwab OAuth flow.

**Rationale**: `authlib` has a `AsyncOAuth2Client` that works with `httpx` and handles PKCE, state parameter, and token refresh. Avoids adding a new dependency and follows the same pattern already used for Google.

### Deduplication strategy

**Decision**: Deduplicate by `(broker_id, user_id)` where `broker_id` is Schwab's order ID stored in a new `broker_order_id` column on `trades`.

**Rationale**: The existing CSV importer doesn't have a persistent external ID to check against; it relies on `(symbol, closed_at, pnl)` fuzzy matching which can produce false duplicates. Schwab's API provides a stable `orderId` that makes exact deduplication reliable. Adding `broker_order_id` to the `trades` table (nullable, for backwards compatibility) is the right long-term approach.

### Trade normalization

**Decision**: Implement a dedicated `SchwabOrderNormalizer` class in `backend/app/utils/schwab_normalizer.py` that maps Schwab `Order` JSON objects to `TradeCreate` Pydantic schemas.

**Rationale**: The CSV importer already has a `SchwabCsvParser` — keeping normalization separate from API fetching follows single-responsibility. The normalizer can be unit-tested with fixture JSON without making real API calls.

## Risks / Trade-offs

- [Schwab API rate limits] Schwab enforces rate limits on the Individual Trader API (120 requests/minute) → Sync endpoint fetches the last 60 days of orders in a single paginated call; no loop required for typical use
- [Token refresh failure] If the refresh token expires (Schwab refresh tokens last 7 days) the user must reconnect → Surface a clear "reconnect required" error on sync failure; show last-sync timestamp on the connections page
- [PKCE state parameter] OAuth state must be stored server-side during the connect flow → Store state in the user's session (or a short-lived DB record); the existing Google OAuth flow uses the same pattern
- [Schwab API changes] Schwab's Individual Trader API is relatively new and may change → Pin to API version in the base URL; document the API version used
- [Migration required] Adding `broker_order_id` to `trades` and creating `broker_connections` table requires migration `0008` → Nullable column + new table; fully backwards-compatible
