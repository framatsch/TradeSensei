## Verification: mcp-integration

**Verified against**: `proposal.md`, `design.md`, `specs/pat-management/spec.md`, `specs/mcp-integration/spec.md`, `tasks.md`

### Goal attainment
The change delivers a complete Personal Access Token system with backend model + API + auth dependency, MCP transport endpoints (SSE + messages), and a frontend settings UI for token management. All 12 tasks in `tasks.md` are marked complete and verified.

---

### Spec coverage by requirement

#### pat-management

| Requirement | Status | Notes |
|---|---|---|
| Personal Access Token Model (id, user_id, name, token_hash, created_at, expires_at, is_revoked, last_used_at) | ✅ Pass | `backend/app/models/pat.py:17` — all fields with correct types; SHA-256 hash in `token_hash` column |
| `GET /api/v1/settings/tokens` — list tokens, no hash exposed | ✅ Pass | `backend/app/api/v1/settings.py:79` — `PatRead` schema (`pat.py:25`) excludes `token_hash` |
| `POST /api/v1/settings/tokens` — generate, return plaintext once | ✅ Pass | `backend/app/api/v1/settings.py:33` — `PatGenerateResponse` (`pat.py:42`) includes plaintext `token` field; `generate_pat()` uses `secrets.token_urlsafe(48)` |
| `DELETE /api/v1/settings/tokens/{id}` — soft revoke | ✅ Pass | `backend/app/api/v1/settings.py:94` → `pat_repository.py:80` sets `is_revoked = True` |
| Token Management UI (generate, list, revoke) | ✅ Pass | `SettingsPageClient.tsx:96` "API & Tokens" tab → `ApiTokensSettings.tsx` → `TokenList.tsx` (table with Name/Created/Expires/Last Used/Status/Action), `GenerateTokenModal.tsx` (name + expiration form), `TokenDisplayModal.tsx` (plaintext + Copy + warning) |

#### mcp-integration

| Requirement | Status | Notes |
|---|---|---|
| `GET /mcp/sse` — persistent SSE with PAT auth + session_id | ✅ Pass | `backend/app/api/mcp.py:63` — persistent `StreamingResponse` with 15s keepalive, optional `session_id` query param, `Connection: keep-alive` + `X-Accel-Buffering: no` headers |
| `POST /mcp/messages` — JSON-RPC processing with PAT auth | ✅ Pass | `backend/app/api/mcp.py:78` — handles `initialize`, `ping`, unknown methods (returns -32601); secured via `get_current_user_from_pat`; accepts optional `session_id` |
| PAT Authentication Dependency (hash → lookup → verify → inject User) | ✅ Pass | `backend/app/core/deps.py:116` — hashes Bearer token, `WHERE token_hash = ?` lookup, `hmac.compare_digest()`, checks `is_revoked` + `expires_at`, updates `last_used_at`, injects `User` |

---

### Design decision compliance

| Decision | Implemented? |
|---|---|
| SHA-256 (not bcrypt) for deterministic `WHERE token_hash = ?` lookup | ✅ `security.py:70` — `hashlib.sha256(token.encode()).hexdigest()` |
| `secrets.token_urlsafe()` for high-entropy generation | ✅ `security.py:67` — `token_urlsafe(48)` |
| Soft revoke (`is_revoked = True`) preserves audit history | ✅ `pat_repository.py:80` |
| `hmac.compare_digest()` against timing attacks | ✅ `deps.py:141` |
| MCP router mounted outside `/api/v1` prefix | ✅ `main.py:106` — `application.include_router(mcp_router)` |
| Audit events: `pat.created` and `pat.revoked` in service layer | ✅ `pat_service.py:52,76` — logs `token_id`, never the token value |
| Pydantic schemas never expose `token_hash` | ✅ `PatRead` in `pat.py:25` — only id, name, created_at, expires_at, is_revoked, last_used_at |

---

### Test coverage

**Backend** (`backend/tests/test_pat_api.py`):
- ✅ PAT CRUD: create, list, revoke integration test
- ✅ Valid PAT auth with MCP endpoint + `last_used_at` update verification
- ✅ Expired token rejection (401)
- ✅ Revoked token rejection (401)
- ✅ Missing token rejection (401)

**Frontend** (`frontend/__tests__/components/settings/ApiTokensSettings.test.tsx`) — 20 tests:
- ✅ ApiTokensSettings rendering: header, description, "Generate New Token" button, token table columns
- ✅ TokenList rendering: token names, Active/Expired/Revoked status badges, Revoke button visibility
- ✅ TokenList states: loading spinner, error message, empty state message
- ✅ GenerateTokenModal: open/close, empty-name validation, successful submit flow
- ✅ TokenDisplayModal: token display, warning text, Copy/Close buttons, close behavior
- ✅ Token revocation: confirm dialog, revoke call, cancel behavior

---

### Migration

| Check | Status |
|---|---|
| Alembic revision exists | ✅ `e3a9f3db71c1_add_personal_access_tokens_table.py` |
| `down_revision` chain valid | ✅ Points to `2f9b7d3a91cd` (exists) |
| Upgrade creates table + indexes | ✅ `personal_access_tokens` table with FK to `users.id`, indexes on `user_id` and `(user_id, created_at)` |
| Downgrade reverses correctly | ✅ Drops indexes then table |

---

### Gaps (all resolved)

1. ~~⚠️ SSE connection is transient~~ → ✅ **Resolved**. `GET /mcp/sse` now returns a persistent `StreamingResponse` with 15-second keepalive comments and proper SSE headers (`Connection: keep-alive`, `X-Accel-Buffering: no`).
2. ~~❌ No frontend tests~~ → ✅ **Resolved**. 20 Jest tests in `__tests__/components/settings/ApiTokensSettings.test.tsx` covering rendering, states, modals, and revocation flow.
3. ~~⚠️ No session ID support~~ → ✅ **Resolved**. `GET /mcp/sse` and `POST /mcp/messages` accept an optional `session_id` query parameter. When provided, the ready event includes `session_id` and the `message_endpoint` URL carries the session ID for downstream routing.
