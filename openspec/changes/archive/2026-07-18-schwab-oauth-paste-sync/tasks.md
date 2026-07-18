## 1. Config & Constants

- [x] 1.1 Add well-known account-property key constants for Schwab OAuth tokens (`SCHWAB_ACCESS_TOKEN`, `SCHWAB_REFRESH_TOKEN`, `SCHWAB_TOKEN_EXPIRES_AT`) and correlation keys (`SCHWAB_OAUTH_CODE_VERIFIER`, `SCHWAB_OAUTH_STATE`) in `backend/app/core/constants.py`
- [x] 1.2 Add `schwab_oauth_mode` setting (`paste`|`callback`, default `paste`) and confirm/adjust `schwab_redirect_uri` default `https://127.0.0.1` in `backend/app/core/config.py`; deprecate/remove global `schwab_client_id`/`schwab_client_secret` as OAuth sources
- [x] 1.3 Change `SchwabClient.get_authorization_url`/`exchange_code`/`refresh_access_token` to accept `client_id`, `client_secret`, and `redirect_uri` as explicit parameters instead of reading `settings.schwab_client_id/secret`; update all call sites
- [x] 1.4 Verify PKCE helper exists (code verifier + S256 challenge); add a small util in `backend/app/utils/` if `SchwabClient` does not already generate the verifier
- [x] 1.5 Add a redirect-URI loopback check helper and validate mode↔redirect_uri consistency (callback ⇒ non-loopback TLS URL; paste ⇒ loopback) used by the authorize flow

## 2. Token Storage & Refresh (Service Layer)

- [x] 2.1 Add `AccountProperty` upsert/delete helpers to the account repository (or reuse existing) so token/correlation properties can be written, read, and cleared by key
- [x] 2.2 Implement `BrokerService._get_valid_schwab_access_token(account)` that reads `SCHWAB_ACCESS_TOKEN`/`SCHWAB_TOKEN_EXPIRES_AT`, refreshes via `SchwabClient.refresh_access_token` (using the account's decrypted `SCHWAB_APP_KEY`/`SCHWAB_APP_SECRET`) when expired or within a 60s skew, persists rotated token + expiry (+ refresh token if rotated), and returns a valid token
- [x] 2.3 Raise an actionable "reconnect required" `ConfigurationError` when refresh fails due to an invalid/expired refresh token
- [x] 2.4 Fix `BrokerService._sync_schwab` to use `_get_valid_schwab_access_token` instead of passing the App Key
- [x] 2.5 Fix `BrokerService._test_schwab`: when tokens exist, obtain a valid access token via the helper and call `get_account_numbers` (the lightest read; Schwab has no ping endpoint); when no tokens exist, return HTTP 400 "connect via OAuth first" without a network call
- [x] 2.6 Return HTTP 400 with a clear message when a `SCHWAB` account has no stored access/refresh token at sync time

## 3. OAuth Connect Flow (Service Layer)

- [x] 3.1 Implement `BrokerService.start_schwab_authorization(account_id, user_id)` — ownership check (404 on foreign account), validate mode↔redirect_uri consistency (400 on mismatch), generate PKCE verifier + `state`, persist verifier + `state` on the account AND a `state → account_id` correlation lookup (encrypted, overwriting prior), return the authorization URL from `SchwabClient.get_authorization_url`
- [x] 3.2 Implement a shared `BrokerService._exchange_and_store(account, code, state, verifier)` core that exchanges via `SchwabClient.exchange_code` and persists encrypted token properties + clears correlation records; used by both completion paths
- [x] 3.3 Implement `BrokerService.complete_schwab_connection(account_id, user_id, redirect_url)` (paste mode) — parse `code`+`state`, validate `state` against the account's stored value, delegate to `_exchange_and_store`
- [x] 3.4 Implement `BrokerService.complete_schwab_callback(code, state)` (callback mode, no user context) — resolve `account_id` via the `state → account_id` correlation, validate, delegate to `_exchange_and_store`; return the resolved account (for the redirect target) and never expose tokens
- [x] 3.5 Implement `BrokerService.get_schwab_status(account_id, user_id)` and `BrokerService.disconnect_schwab(account_id, user_id)` (delete token properties)
- [x] 3.6 Emit manual audit events `broker.schwab_connected` / `broker.schwab_disconnected` with safe identifiers only (no tokens); ensure no token value is ever logged

## 4. Schemas & API Endpoints

- [x] 4.1 Add Pydantic DTOs in `backend/app/schemas/broker.py`: `SchwabAuthorizeResponse { authorization_url }`, `SchwabCompleteRequest { redirect_url }`, reuse/extend `BrokerStatusResponse` for status
- [x] 4.2 Add `POST /broker/schwab/authorize/{account_id}` route in `backend/app/api/v1/broker.py` (returns authorization URL)
- [x] 4.3 Add `POST /broker/schwab/complete/{account_id}` route (body = pasted redirect URL) mapping `ConfigurationError`/validation to 400 and `AccountNotFoundError` to 404
- [x] 4.4 Add **unauthenticated** `GET /broker/schwab/callback` route (query `code`, `state`) that calls `complete_schwab_callback` and issues an HTTP redirect to the settings page with a success/error flag; must be exempt from the Bearer-auth dependency; on unknown `state`/missing `code`/exchange failure, redirect with an error flag (no 500 leak)
- [x] 4.5 Add `GET /broker/schwab/status/{account_id}` and `DELETE /broker/schwab/connect/{account_id}` routes
- [x] 4.6 Add OpenAPI annotations (summaries, descriptions, response models, 400/401/404 responses) consistent with the existing sync endpoint; document the callback as unauthenticated

## 5. Frontend (Account Settings)

- [x] 5.1 Regenerate the OpenAPI client so the new Schwab endpoints are available (openapi-sync)
- [x] 5.2 Add a "Connect Schwab" action in account settings that requests the authorization URL and opens it. In paste mode, show a paste field with clear copy ("the page will not load — copy the URL and paste it here"); in callback mode, just open the URL and poll/refresh status after the redirect returns to settings
- [x] 5.3 Submit the pasted redirect URL to the complete endpoint (paste mode); reflect connected status from the status endpoint (both modes); handle the callback return via a success/error query flag on the settings page; add a "Disconnect" affordance; surface the "reconnect required" state (expected ~weekly due to Schwab's 7-day refresh-token limit) as a neutral prompt to re-connect, not an error banner
- [x] 5.4 Use semantic Tailwind tokens (no `dark:` modifiers); no raw `fetch()` — use the generated client

## 6. Tests

- [x] 6.1 Unit tests for `_get_valid_schwab_access_token`: valid token passthrough, refresh-on-expiry with persistence, refresh-failure → reconnect error
- [x] 6.2 Unit/service tests for authorize (state+verifier+correlation persisted, foreign account → 404, unconfigured → 400, mode↔redirect mismatch → 400) and paste-complete (valid URL stores tokens + clears correlation; missing code → 400; state mismatch → 400; exchange failure → 400, no partial persist)
- [x] 6.3 Tests for the callback path: valid state resolves account + stores tokens + redirects success; unknown/expired state → redirect error, no exchange; missing code → redirect error; exchange failure → redirect error, no partial persist; callback route is reachable without a Bearer token
- [x] 6.4 Service tests for status (connected/not) and disconnect (properties deleted, audit emitted)
- [x] 6.5 Update `_sync_schwab` and `_test_schwab` tests: assert the access token (not App Key) is used; `_test_schwab` calls `get_account_numbers` when connected and returns 400 "connect first" (no network call) when not connected; missing connection at sync returns 400
- [x] 6.6 Frontend tests for the connect/paste/disconnect UI flow, and the callback-return success/error handling (React Testing Library)

## 7. Docs, Audit & Verification

- [x] 7.1 Document both connect flows in `docs/dev-guide.md` and API usage: obtaining per-account Schwab app credentials; paste mode (`SCHWAB_OAUTH_MODE=paste`, register `https://127.0.0.1`, copy/paste step); callback mode (`SCHWAB_OAUTH_MODE=callback`, register `https://<domain>/api/v1/broker/schwab/callback`, requires ingress TLS on k3s); and reconnect-on-refresh-expiry behavior
- [x] 7.2 Confirm audit coverage (connect/disconnect events) and sensitive-data exclusion per AGENTS.md audit policy
- [x] 7.3 Run lint-check (`ruff` + `mypy --strict`) and the backend test suite; fix findings
- [x] 7.4 Update CHANGELOG.md `[Unreleased]` with the Schwab OAuth connect + sync fix
