## Why

Currently users must manually export CSV files from their Schwab brokerage account and upload them to the journal. This creates friction — users may forget to export, data may lag by days, and the import process requires several manual steps. A direct Schwab API integration allows on-demand and automatic trade sync directly from the brokerage, eliminating the manual export workflow.

## What Changes

- New OAuth 2.0 authorization flow using the Schwab Individual Trader API (redirect → callback → token exchange)
- Schwab credentials (client_id, client_secret, redirect_uri) stored per-user (encrypted) in a new `broker_connections` table
- New endpoint `GET /broker/schwab/connect` — redirects the user to Schwab's OAuth authorization page
- New endpoint `GET /broker/schwab/callback` — handles the OAuth callback, stores tokens
- New endpoint `POST /broker/schwab/sync` — fetches recent trades from the Schwab Orders API, deduplicates, and imports into the journal
- New endpoint `GET /broker/schwab/status` — returns whether the user has a connected Schwab account and last sync time
- New endpoint `DELETE /broker/schwab/disconnect` — revokes and removes stored Schwab credentials

## Capabilities

### New Capabilities

- `schwab-oauth-connect`: OAuth 2.0 connect/callback/disconnect flow for Schwab API
- `schwab-trade-sync`: Fetch recent orders from Schwab Orders API, normalize to `Trade` model, deduplicate, and import
- `broker-connection-model`: `broker_connections` table storing encrypted OAuth tokens per user per broker

### Modified Capabilities

<!-- none -->

## Impact

- **Backend**: New `broker_connections` ORM model + Alembic migration; new `schwab_client.py` in `backend/app/utils/` for Schwab API HTTP calls; new `BrokerService` + `BrokerRepository`; new `backend/app/api/v1/broker.py` router
- **Frontend**: New `dashboard/connections/` page for managing broker connections; new `ConnectSchwabButton` component; new `useSchWabConnection` hook
- **Database**: New `broker_connections` table (migration `0008`)
- **Dependencies**: `httpx` (already present), `cryptography` for token encryption at rest
- **Security**: OAuth tokens stored encrypted in DB; `BROKER_ENCRYPTION_KEY` env var required; token refresh handled automatically on sync
- **Breaking**: None — additive only
