## Why

Schwab live sync is wired up in the API and service layer, but it never obtains a valid OAuth access token: `broker_service._sync_schwab` passes the stored **App Key** to the Schwab REST API as if it were a Bearer access token, so every sync fails. There is no way for a user to authorize the application against Schwab from the running app. The `SchwabClient` already implements the full PKCE OAuth flow (`get_authorization_url`, `exchange_code`, `refresh_access_token`) but nothing is wired to an endpoint.

This change wires up the OAuth flow in **two deployment shapes** that share the same token-exchange core:
- **Paste flow** (local/Docker): uses Schwab's `https://127.0.0.1` loopback redirect exception — no TLS/cert required. The user copies the redirect URL from the browser and pastes it back, exactly as proven in `tools/schwab_cli.py`.
- **Callback flow** (k3s / public domain with real TLS, e.g. cert-manager/Let's Encrypt): a real `GET /schwab/callback` endpoint receives the redirect automatically — no copy-paste. This is the natural fit when a valid certificate already terminates at a public domain.

## What Changes

- Add a **Schwab OAuth "connect" flow** driven from account settings, supporting two modes selected by an explicit `SCHWAB_OAUTH_MODE=paste|callback` setting:
  - **Common start**: Backend generates a PKCE code verifier + `state`, persists them plus a `state → account_id` correlation briefly, and returns the Schwab authorization URL built from the account's app credentials and the configured `redirect_uri`.
  - **Paste mode**: user copies the resulting `https://127.0.0.1?code=...` URL from the browser (the page intentionally does not load) and pastes it back into settings; backend extracts `code`+`state`, validates, exchanges via `SchwabClient.exchange_code`, stores tokens.
  - **Callback mode**: `GET /broker/schwab/callback` receives `code`+`state` automatically from Schwab, looks up the `account_id` via the stored `state` correlation (no Bearer token needed), exchanges, and stores tokens — then redirects the browser back to the settings page.
- Validate at authorization time that `SCHWAB_OAUTH_MODE` and `schwab_redirect_uri` are consistent (callback mode must not use a loopback URL; paste mode expects a loopback URL).
- Store Schwab OAuth tokens **the same way IBKR credentials are stored today** — as Fernet-encrypted `AccountProperty` rows on the account (`SCHWAB_ACCESS_TOKEN`, `SCHWAB_REFRESH_TOKEN`, `SCHWAB_TOKEN_EXPIRES_AT`), alongside the existing `SCHWAB_APP_KEY`/`SCHWAB_APP_SECRET`. No new DB model, no migration.
- **Fix** `broker_service._sync_schwab` to use the stored access token (not the App Key), and to transparently refresh the token via `SchwabClient.refresh_access_token` when it is expired or about to expire, persisting the rotated tokens.
- Add backend endpoints for the connect flow (start authorization + complete-by-paste) and a disconnect/status affordance, all requiring a valid Bearer token and scoped to the authenticated user's account.
- **BREAKING (behavioral):** the `SchwabClient.get_authorization_url` PKCE flow uses the `schwab_redirect_uri` setting; for the paste flow this must be `https://127.0.0.1`. Deployments relying on the old (non-functional) App-Key-as-token assumption will now require an explicit connect step.

## Capabilities

### New Capabilities
- `schwab-oauth-connect`: Browser-driven Schwab OAuth authorization for an account via PKCE, in two modes (paste for loopback/no-TLS deployments; automatic callback for public-domain deployments with real TLS), with `state → account_id` correlation, encrypted token storage as account properties, and token refresh on sync.

### Modified Capabilities
- `account-centric-broker-sync`: The "Syncing a Schwab Account" behavior changes — the sync SHALL look up and use the decrypted **access token** (refreshing it when expired) instead of treating the App Key as the Bearer token.

## Impact

- **New/changed backend endpoints** under `/api/v1/broker/schwab/...`: authorize (start), complete-by-paste (`POST`), callback (`GET`, unauthenticated, correlated by `state`), status, disconnect — in `backend/app/api/v1/broker.py`.
- **`backend/app/services/broker_service.py`** — `_sync_schwab` credential resolution and token-refresh logic; new connect/exchange service methods.
- **`backend/app/utils/schwab_client.py`** — reused as-is (PKCE + exchange + refresh already implemented); no HTTP-shape changes expected.
- **Account properties** — three new well-known keys (`SCHWAB_ACCESS_TOKEN`, `SCHWAB_REFRESH_TOKEN`, `SCHWAB_TOKEN_EXPIRES_AT`); no schema change (generic key-value table).
- **Config** — new `schwab_oauth_mode` setting (`paste`|`callback`, default `paste`); `schwab_redirect_uri` default `https://127.0.0.1` (central setting, must string-match the Schwab app registration). OAuth `client_id`/`client_secret` come from per-account `SCHWAB_APP_KEY`/`SCHWAB_APP_SECRET` (like IBKR); global `SCHWAB_CLIENT_ID`/`SCHWAB_CLIENT_SECRET` settings are **deprecated** as OAuth sources.
- **`SchwabClient` signature change** — `get_authorization_url`, `exchange_code`, and `refresh_access_token` take `client_id`/`client_secret`/`redirect_uri` as explicit parameters instead of reading global settings.
- **Frontend** — account settings gains a "Connect Schwab" action: request authorization URL, show paste field, submit the redirect URL. Uses the OpenAPI-generated client.
- **Docs** — dev guide + api-usage: obtaining Schwab app credentials; paste mode (loopback `https://127.0.0.1` registration + copy/paste step); callback mode (register the public `https://<domain>/api/v1/broker/schwab/callback` URL, requires real TLS at the ingress — e.g. cert-manager/Let's Encrypt on k3s). **No nginx/self-signed-cert overlay is shipped**: paste mode needs no TLS, and callback mode relies on the deployment's existing ingress TLS.
- **Audit logging** — connect/disconnect are non-CRUD complex operations; emit manual audit events (`broker.schwab_connected`, `broker.schwab_disconnected`) with safe identifiers only (no tokens).
