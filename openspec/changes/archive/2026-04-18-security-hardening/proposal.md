## Why

Five security issues must be resolved before any public or multi-user
deployment. The most critical is IDOR (Insecure Direct Object Reference):
if a user obtains another user's resource UUID — through a leak, guess, or
any means — they must not be able to read or mutate that resource via the
REST API. The remaining four cover token replay, cursor manipulation, a
plaintext password in process arguments, and overly broad exception handling
that silently swallows auth bugs.

1. **IDOR — no systematic ownership enforcement**: REST endpoints accept a
   resource ID and look it up by ID only. No repository method structurally
   requires a `user_id` filter. A user with a valid JWT and another user's
   trade UUID gets the trade data.

2. **OTT Blocklist in-memory**: `_used_ott_jti: set[str]` is not shared
   across processes. In multi-worker deployments a one-time token can be
   replayed through a different process.

3. **Cursor pagination not user-scoped or signed**: The cursor encodes
   `sort_field_value + trade_id` with no HMAC and no guaranteed `user_id`
   filter on decode. A manipulated cursor can enumerate another user's data.

4. **Password in CLI arguments**: `reset_password.py` exposes the new password
   in `ps aux`, shell history, systemd journal, and audit logs.

5. **Broad `except Exception` in `security.py`**: swallows unexpected errors
   that should surface as 500s in logs.

## What Changes

### Authorization (IDOR prevention)
- All repository `get_by_id` / `update` / `delete` methods gain a required
  `user_id: int` parameter — structurally impossible to call without it.
- All resource endpoints return `404 Not Found` (not `403`) when a resource
  belongs to another user — no information leak about existence.
- PostgreSQL Row-Level Security (RLS) enabled on all user-scoped tables as a
  DB-layer safety net — blocks even application-layer bugs.
- Ownership test fixture added to `conftest.py`; `GET/PATCH/DELETE` ownership
  test added for every resource endpoint.

### OTT / Cursor / CLI / Exception fixes
- New DB table `used_otts(jti, expires_at)` replaces in-memory set.
- All paginated list queries gain unconditional `AND user_id = :uid` guard
  + HMAC-signed cursors.
- `reset_password.py` uses `getpass.getpass()` — `-p` argument removed.
- `security.py`: `except (JWTError, ValueError)` — bare `Exception` removed.

## Capabilities

### New Capabilities
- `authorization` — systematic IDOR prevention via repository pattern + RLS.
- `ott-blocklist-persistent` — DB-backed OTT deduplication.

### Modified Capabilities
- `cursor-pagination` — user_id guard + HMAC signing.
- `password-reset-cli` — interactive password input.
- All resource endpoints — 404 on cross-user access (not 403).

## Impact

- **Backend**: all repository classes, all resource route handlers, `security.py`,
  `reset_password.py`, new Alembic migrations.
- **Database**: `used_otts` table; RLS policies on all user-scoped tables.
- **Tests**: ownership test for every resource endpoint (~10 resources × 3
  methods = ~30 new test cases).
- **Dependencies**: no new dependencies.
- **Deployment**: backward compatible; existing sessions unaffected.
