## 1. Database Model and Migration

- [x] 1.1 Create `BrokerConnection` SQLAlchemy ORM model in `backend/app/models/broker_connection.py`: `id`, `user_id` (FK), `broker` (string), `access_token` (text), `refresh_token` (text), `token_expires_at` (timestamp), `last_sync_at` (timestamp nullable), `created_at`, `updated_at`; unique constraint on `(user_id, broker)`
- [x] 1.2 Add `broker_order_id` nullable column to `Trade` model (`backend/app/models/trade.py`)
- [x] 1.3 Create Alembic migration `0008_broker_connections.py`: CREATE TABLE `broker_connections`, ADD COLUMN `broker_order_id` to `trades`, ADD unique index on `(user_id, broker)` in `broker_connections`
- [x] 1.4 Apply migration locally and verify with `alembic upgrade head`

## 2. Configuration

- [x] 2.1 Add `BROKER_ENCRYPTION_KEY: str` to `backend/app/core/config.py` Settings class (fail fast if missing)
- [x] 2.2 Add `SCHWAB_CLIENT_ID: str`, `SCHWAB_CLIENT_SECRET: str`, `SCHWAB_REDIRECT_URI: str` to Settings
- [x] 2.3 Update `.env.example` / `docker-compose.yml` with the new env vars

## 3. Encryption Utility

- [x] 3.1 Create `backend/app/utils/encryption.py` with `encrypt_token(plaintext: str) -> str` and `decrypt_token(ciphertext: str) -> str` using `cryptography.fernet`
- [x] 3.2 Add `cryptography` to `backend/pyproject.toml` dependencies

## 4. Schwab API Client

- [x] 4.1 Create `backend/app/utils/schwab_client.py` with `SchwabClient` class: `get_authorization_url(state, code_challenge)`, `exchange_code(code, code_verifier)`, `refresh_access_token(refresh_token)`, `get_orders(access_token, from_date, to_date)`
- [x] 4.2 Create `backend/app/utils/schwab_normalizer.py` with `SchwabOrderNormalizer.normalize(order_json) -> TradeCreate | None` (returns None for non-filled or unsupported order types)

## 5. Repository

- [x] 5.1 Create `backend/app/repositories/broker_connection_repository.py` with: `get_by_user_broker(user_id, broker)`, `upsert(user_id, broker, access_token, refresh_token, token_expires_at)`, `update_last_sync(user_id, broker)`, `delete(user_id, broker)`

## 6. Service

- [x] 6.1 Create `backend/app/services/broker_service.py` with `BrokerService`:
  - `get_schwab_connect_url(user_id) -> str` — generates PKCE, stores state, returns authorization URL
  - `handle_schwab_callback(code, state) -> None` — validates state, exchanges code, stores encrypted tokens
  - `disconnect_schwab(user_id) -> None` — deletes connection record
  - `get_schwab_status(user_id) -> BrokerStatusResponse`
  - `sync_schwab_trades(user_id, days) -> SyncResult` — refresh token if needed, fetch orders, normalize, deduplicate by `broker_order_id`, insert new trades

## 7. API Routes

- [x] 7.1 Create `backend/app/api/v1/broker.py` router with endpoints:
  - `GET /broker/schwab/connect` → redirect response
  - `GET /broker/schwab/callback` → handles OAuth callback, redirects to frontend
  - `POST /broker/schwab/sync` → returns `SyncResult`
  - `GET /broker/schwab/status` → returns `BrokerStatusResponse`
  - `DELETE /broker/schwab/disconnect` → returns 204
- [x] 7.2 Register the broker router in `backend/app/main.py`

## 8. Backend Schemas

- [x] 8.1 Add `BrokerStatusResponse` Pydantic schema: `connected: bool`, `last_sync_at: datetime | None`
- [x] 8.2 Add `SchwabSyncResult` Pydantic schema: `imported_count: int`, `skipped_count: int`, `errors: list[str]`

## 9. Backend Tests

- [x] 9.1 Write unit tests for `SchwabOrderNormalizer.normalize` with fixture JSON (filled equity order, option order, partial fill, unsupported type)
- [x] 9.2 Write unit tests for `encryption.py` (encrypt/decrypt roundtrip)
- [x] 9.3 Write unit tests for `BrokerService.sync_schwab_trades` (mock client + repo, verify deduplication, token refresh path)
- [x] 9.4 Write API tests for `GET /broker/schwab/status` (connected / disconnected)
- [x] 9.5 Write API tests for `DELETE /broker/schwab/disconnect` (200, 404 if no connection)
- [x] 9.6 Write API tests for `POST /broker/schwab/sync` (404 no connection, 401 expired refresh token)

## 10. OpenAPI Client Sync

- [x] 10.1 Run `openapi-sync` skill to regenerate the frontend TypeScript API client (project uses handwritten api.ts; added BrokerStatusResponse and SchwabSyncResult to lib/types.ts)

## 11. Frontend Connections Page

- [x] 11.1 Create `frontend/app/dashboard/connections/page.tsx` — shows connected broker integrations
- [x] 11.2 Create `frontend/components/broker/ConnectSchwabButton.tsx` — "Connect Schwab" button that links to `GET /broker/schwab/connect`
- [x] 11.3 Create `frontend/components/broker/SchwabConnectionCard.tsx` — shows connection status, last sync time, "Sync Now" button, "Disconnect" button
- [x] 11.4 Create `frontend/hooks/useSchwabConnection.ts` — React Query hooks for `useSchwabStatus`, `useSchwabSync`, `useDisconnectSchwab`
- [x] 11.5 Add "Connections" link to the dashboard sidebar navigation

## 12. Lint, Types, and Commit

- [x] 12.1 Run `lint-check` skill — fix all ruff and mypy errors (pre-existing ruff errors in legacy files only; new files are clean)
- [x] 12.2 Run `unit-test` skill — ensure all tests pass (68 frontend tests, backend tests pass)
- [x] 12.3 Create git commit using `commit-helper` skill
