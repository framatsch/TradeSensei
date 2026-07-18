## Context

Schwab live sync exists in the API (`POST /broker/sync/{account_id}`) and service (`BrokerService._sync_schwab`) but is non-functional: it passes the stored **App Key** to the Schwab REST API as a Bearer access token. The real OAuth building blocks already exist and are unused — `SchwabClient` (`backend/app/utils/schwab_client.py`) implements `get_authorization_url` (PKCE), `exchange_code`, and `refresh_access_token`. The working CLI (`tools/schwab_cli.py`) proves the paste-the-redirect-URL model against Schwab's `https://127.0.0.1` loopback redirect, which is exempt from the "public HTTPS with valid cert" requirement.

Credentials today are stored uniformly as Fernet-encrypted `AccountProperty` key-value rows (IBKR: `IBKR_FLEX_TOKEN`, `IBKR_FLEX_QUERY_ID`; Schwab app creds: `SCHWAB_APP_KEY`, `SCHWAB_APP_SECRET`). The `account_properties` table has a `(account_id, key)` unique constraint and is a generic encrypted KV store.

Constraints: self-hosted, Docker-first; adding TLS/nginx + certificate import is friction we want to avoid. `mypy --strict` and the layered architecture (routes → services → repositories) are non-negotiable.

## Goals / Non-Goals

**Goals:**
- Let a user connect a Schwab account from settings in both deployment shapes: paste mode (loopback, no TLS) for local/Docker, and automatic callback mode for public-domain deployments (k3s) with real ingress TLS.
- Store OAuth tokens uniformly with existing broker credentials (encrypted `AccountProperty` rows), no new model or migration.
- Make Schwab sync actually work: use the access token, refresh transparently on expiry.
- Reuse the existing `SchwabClient` PKCE/exchange/refresh methods without changing their HTTP shapes.

**Non-Goals:**
- No shipped nginx/self-signed-cert Compose overlay. Paste mode needs no TLS; callback mode relies on the deployment's own ingress TLS (e.g. cert-manager/Let's Encrypt on k3s), which is the operator's responsibility, not this change's.
- No background/scheduled token refresh — refresh happens lazily just-in-time before broker calls.
- No new broker types; Schwab only.

## Decisions

### D0: Per-account app credentials + centrally-configured redirect URI
The OAuth `client_id`/`client_secret` come from the account's own encrypted `SCHWAB_APP_KEY`/`SCHWAB_APP_SECRET` properties (per-account, exactly like IBKR's `IBKR_FLEX_TOKEN`/`IBKR_FLEX_QUERY_ID`). The `redirect_uri` comes from the central `schwab_redirect_uri` setting (default `https://127.0.0.1`).
- **Why (creds):** Consistency with IBKR and the existing account-property model; supports distinct Schwab app registrations per account/tenant; no global-vs-account ambiguity.
- **Why (redirect):** The redirect URI must string-match a URL registered in the Schwab developer app; it is an instance-wide constant, not per-account data. A setting (not a UI field, not free-generated) keeps it authoritative and lets a future real-callback flow reuse the same value.
- **Consequence:** `SchwabClient.get_authorization_url`, `exchange_code`, and `refresh_access_token` MUST accept `client_id`, `client_secret`, and `redirect_uri` as explicit parameters instead of reading `settings.schwab_client_id/secret`. The global `SCHWAB_CLIENT_ID`/`SCHWAB_CLIENT_SECRET` settings are deprecated/removed as OAuth credential sources.
- **Alternative considered:** global app credentials in settings. Rejected: diverges from IBKR, blocks per-account app registration.
- **Alternative considered:** per-account redirect URI. Rejected: the redirect is registered once with Schwab; per-account values would all have to be identical anyway.

### D1: Two completion modes (paste + callback) selected by explicit config, sharing one exchange core
The connect flow has a common start (authorize) and two possible completions, chosen by the `schwab_oauth_mode` setting:
- **paste** (local/Docker): Schwab permits `https://127.0.0.1` as a registered redirect URI without a valid public certificate. The browser lands on a non-loading loopback page; the user copies the URL (`https://127.0.0.1/?code=...&state=...`) and pastes it into a Bearer-authenticated `POST /complete`. Zero TLS/cert setup; proven by `tools/schwab_cli.py`.
- **callback** (k3s / public domain): a real `GET /broker/schwab/callback` receives the redirect automatically. This requires a valid TLS cert at the ingress — which a public-domain deployment already has (cert-manager/Let's Encrypt) — so no self-signed cert or browser cert-import is involved.

Both modes funnel `code`+`state` into the same `exchange_code` + token-persist path. The only differences are (a) how `code`/`state` arrive and (b) that the callback has no Bearer token and must correlate the account via `state` (see D3).
- **Why explicit `SCHWAB_OAUTH_MODE=paste|callback` rather than inferring from the URL:** the operator's intent is unambiguous, and the authorize endpoint can hard-fail on inconsistent config (callback + loopback URL, or paste + public URL) instead of silently guessing.
- **Consistency guard:** at authorize time, reject callback mode with a loopback `schwab_redirect_uri` (400), since the automatic redirect could never reach the server.
- **Note on loopback conflicts:** `https://127.0.0.1` may already be occupied by a local service (e.g. on Windows); because the redirect URI is a configurable setting, the operator can register and use a different loopback port/host — another reason the redirect is a setting, not a hardcoded constant.
- **Not shipped:** no nginx/self-signed-cert Compose overlay. Paste needs no TLS; callback relies on the deployment's existing ingress TLS.

### D2: Store tokens as encrypted `AccountProperty` rows (consistent with IBKR)
New well-known keys on the account: `SCHWAB_ACCESS_TOKEN`, `SCHWAB_REFRESH_TOKEN`, `SCHWAB_TOKEN_EXPIRES_AT` (ISO-8601 UTC string). Reuse `encrypt_token`/`decrypt_token` and the same resolve/upsert pattern as `SCHWAB_APP_KEY`.
- **Why:** Uniform with IBKR and existing Schwab app creds; the KV table is designed for exactly this; no migration; RLS/ownership already enforced on the account.
- **Alternative considered:** dedicated `broker_connections` table + Alembic migration. Rejected: diverges from the established account-property pattern for no functional gain and adds migration surface.

### D3: PKCE verifier + `state → account_id` correlation storage
The connect flow is two calls (start → complete), so the `code_verifier` and `state` must survive between them. Store them as short-lived encrypted `AccountProperty` rows (`SCHWAB_OAUTH_CODE_VERIFIER`, `SCHWAB_OAUTH_STATE`) keyed to the account, and delete them on completion.

Crucially, the **callback** completion arrives with no Bearer token — only Schwab's `code`+`state`. So the system must resolve the account from `state` alone. The chosen approach: persist a `state → account_id` lookup at authorize time (server-side, encrypted), and resolve it in the callback. The `state` is validated to match the per-account stored `state` before any exchange.
- **Why (state→account lookup over signed/JWT state):** reuses the same encrypted storage already needed for verifier/state; no new signing key or token-format logic; state stays short. The lookup is one-time and cleared on completion.
- **Why not Starlette session middleware:** the paste `POST /complete` is a token-authenticated SPA call, and the callback is a cookie-less server-to-browser redirect from Schwab; account-scoped property storage covers both cleanly and supports multiple accounts.
- **Trade-off:** the `state → account_id` record must be resolvable without auth in callback mode, so it lives in a lookup keyed by `state` (not only by account). Mitigate: random high-entropy `state`, short TTL, single-use (deleted on completion), never returns token data.
- **Trade-off:** verifier/state persist until overwritten or completion; mitigate by overwriting on each new "start" and clearing on completion.

### D4: Lazy just-in-time refresh in a single helper
Add a service helper that returns a valid access token for an account: read `SCHWAB_TOKEN_EXPIRES_AT`; if past (or within a small skew, e.g. 60s), call `refresh_access_token` with the account's `SCHWAB_APP_KEY`/`SCHWAB_APP_SECRET`, persist the rotated token + expiry (+ refresh token if Schwab rotates it), and return the fresh token. `_sync_schwab` and `_test_schwab` call this instead of using the App Key as the token.
- **Why:** One place owns refresh + persistence; fixes the core bug and satisfies the "transparent refresh" requirement.
- **Token lifetimes (confirmed via Schwab docs + multiple SDKs):** access token = 30 minutes; refresh token = a hard 7-day limit from creation, not extendable, not an idle timeout. When the refresh call returns `invalid_client` (expired refresh token), the helper raises the "reconnect required" error — a normal, recurring event, not an exceptional failure.

### D4b: Test-connection uses `get_account_numbers` with a valid token (no dedicated ping)
The Schwab Trader API has no health/ping endpoint. The lightest authenticated read is `GET /accounts/accountNumbers`, which returns only account-number→hash mappings. `_test_schwab` SHALL obtain a valid access token via the D4 helper (refreshing if needed) and call `get_account_numbers`; success means the connection is live.
- **Why:** Unlike IBKR (static Flex token/query ID that can be validated directly), Schwab has no usable API credential before OAuth — App Key/Secret alone cannot authenticate a request. So a Schwab test-connection is only meaningful *after* connect.
- **Before connect:** if the account has no stored access/refresh token, `_test_schwab` SHALL return a clear "connect via OAuth first" error (HTTP 400) without a network call.
- **Fixes the same bug as sync:** the current `_test_schwab` passes the App Key as the access token; it is corrected to use the real token.

### D5: Endpoint surface under `/api/v1/broker/schwab`
- `POST /broker/schwab/authorize/{account_id}` → returns `{ authorization_url }`. Bearer-authenticated, ownership-checked.
- `POST /broker/schwab/complete/{account_id}` → body `{ redirect_url }`; paste mode; Bearer-authenticated, ownership-checked; exchanges + stores tokens.
- `GET  /broker/schwab/callback` → **unauthenticated**; callback mode; reads `code`+`state`, resolves account via `state` correlation, exchanges, stores, then HTTP-redirects the browser to the settings page with a success/error flag.
- `GET  /broker/schwab/status/{account_id}` → `{ connected: bool }`. Bearer-authenticated.
- `DELETE /broker/schwab/connect/{account_id}` → disconnect (delete token props). Bearer-authenticated.
All exchange/persist logic lives in `BrokerService`; the callback route is thin and never exposes tokens. Only the callback is unauthenticated (by OAuth necessity); it acts solely on a matching stored `state`.

## Risks / Trade-offs

- **[User pastes the wrong/expired URL]** → Validate presence of `code` and matching `state`; return actionable 400s. The auth `code` is single-use and short-lived, so a stale paste fails cleanly at exchange time.
- **[Refresh token expiry — hard 7-day limit for Schwab, confirmed]** → Access tokens last 30 min (auto-refreshed); refresh tokens expire 7 days after creation and cannot be extended. On the resulting `invalid_client`, surface a clear "reconnect required" prompt; the user re-runs the connect flow. This recurs weekly by design, so the UI treats it as an expected state, not an error. No silent stuck state.
- **[`state`/verifier persistence leak]** → Overwrite on each `authorize`, delete on `complete`; values are encrypted at rest.
- **[Loopback redirect confuses users (paste mode)]** → Document clearly (dev guide + settings UI copy): the page will NOT load; copy the URL immediately, mirroring the CLI's existing guidance.
- **[Unauthenticated callback endpoint (callback mode)]** → Acts only on a matching, single-use, high-entropy `state`; performs no action and reveals nothing when `state` is unknown; never returns tokens; redirects to a fixed settings URL. Effectively a CSRF-guarded, correlation-only endpoint.
- **[Mode/redirect misconfiguration]** → Authorize endpoint validates mode↔redirect_uri consistency and returns a 400 that names the mismatch, so it fails at connect time rather than silently at Schwab.
- **[Existing spec assumed App Key as token]** → Superseded by the MODIFIED `account-centric-broker-sync` delta; the old behavior never worked, so no real regression.
- **[Token values leaking into logs/responses]** → Enforce: never log token values; status/connect responses expose only booleans and safe IDs; audit events carry only `account_id`/`user_id`; the callback never puts tokens in the redirect URL.

## Migration Plan

1. Ship backend endpoints (authorize / complete-paste / callback / status / disconnect) + service refresh helper + `_sync_schwab` fix (backward-compatible: new keys, no schema change).
2. Configure per deployment shape:
   - **Local/Docker (paste):** `SCHWAB_OAUTH_MODE=paste`, `SCHWAB_REDIRECT_URI=https://127.0.0.1` (or an alternate free loopback port), register that URL in the Schwab app.
   - **k3s/public (callback):** `SCHWAB_OAUTH_MODE=callback`, `SCHWAB_REDIRECT_URI=https://<domain>/api/v1/broker/schwab/callback` (ingress must terminate real TLS), register that URL in the Schwab app.
   - Both: each account must store `SCHWAB_APP_KEY`/`SCHWAB_APP_SECRET` before connecting.
3. Frontend adds the connect action in account settings via the regenerated OpenAPI client; in callback mode it just opens the authorization URL and waits for the redirect back, in paste mode it shows the paste field.
4. Rollback: revert endpoints + service change; stored token properties are inert if unused. No data migration to undo.

## Open Questions

- **Resolved:** Per-account app credentials are used (`SCHWAB_APP_KEY`/`SCHWAB_APP_SECRET`), consistent with IBKR; global `SCHWAB_CLIENT_ID`/`SCHWAB_CLIENT_SECRET` are deprecated as OAuth sources. `SchwabClient` OAuth methods take `client_id`/`client_secret`/`redirect_uri` as parameters.
- **Resolved:** Redirect URI is taken from the central `schwab_redirect_uri` setting (default `https://127.0.0.1`) — not a per-account field and not auto-generated, because it must string-match the URL registered in the Schwab developer app.
- **Resolved:** Schwab access token = 30 min; refresh token = hard 7-day limit from creation, not extendable (confirmed via Schwab developer docs and multiple community SDKs). UX copy frames weekly reconnect as expected, not an error.
- **Resolved:** Schwab test-connection = `get_account_numbers` with a valid token (no ping endpoint exists); returns "connect first" before OAuth is completed.
