## Decision 1: Repository Pattern with Required `user_id`

**Problem**: Repository methods currently accept only the resource ID. Nothing
in the call signature enforces that the caller passes a user context. A
missing `user_id` filter is a silent bug that compiles and runs without error.

**Decision**: Every repository method that loads or mutates a single resource
by ID receives `user_id: int` as a **required positional parameter** — not
optional, not keyword-with-default. The SQL always includes
`WHERE id = :id AND user_id = :uid`.

```python
class TradeRepository:
    async def get_by_id(
        self, trade_id: UUID, user_id: int       # required — no default
    ) -> Trade | None:
        result = await self.db.execute(
            select(Trade).where(
                Trade.id == trade_id,
                Trade.user_id == user_id          # always present
            )
        )
        return result.scalar_one_or_none()

    async def update(
        self, trade_id: UUID, user_id: int, data: TradeUpdate
    ) -> Trade | None: ...

    async def delete(self, trade_id: UUID, user_id: int) -> bool: ...
```

Calling `repo.get_by_id(trade_id)` without `user_id` raises a `TypeError` —
not a data leak at runtime. The secure path is the path of least resistance.

**On cross-user access**: query returns `None` → service raises `NotFoundError`
→ route handler returns **404 Not Found** (not 403 — 403 leaks that the
resource exists; 404 does not).

**Scope**: `TradeRepository`, `ExecutionRepository`, `AccountRepository`,
`PlaybookRepository`, `TagRepository`, `NoteRepository`, `ScreenshotRepository`,
`BrokerRawTransactionRepository`.

---

## Decision 2: PostgreSQL Row-Level Security (Defense in Depth)

**Problem**: Application code can have bugs. A missing `user_id` in a raw SQL
query would silently return another user's data with no second check.

**Decision**: Enable RLS on all user-scoped tables. The DB refuses to return
rows where `user_id ≠ current_setting('app.current_user_id')`, regardless of
what SQL the application sends.

```sql
ALTER TABLE trades               ENABLE ROW LEVEL SECURITY;
ALTER TABLE logical_executions   ENABLE ROW LEVEL SECURITY;
ALTER TABLE broker_raw_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE accounts             ENABLE ROW LEVEL SECURITY;
ALTER TABLE playbooks            ENABLE ROW LEVEL SECURITY;
ALTER TABLE tags                 ENABLE ROW LEVEL SECURITY;
ALTER TABLE trade_notes          ENABLE ROW LEVEL SECURITY;
ALTER TABLE screenshots          ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_settings        ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_isolation ON trades
    USING (user_id = current_setting('app.current_user_id', true)::int);
-- repeat for each table above
```

**Setting context per request** — FastAPI dependency replacing `get_db` on all
authenticated routes:

```python
async def get_db_with_rls(
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator[AsyncSession, None]:
    await db.execute(
        text("SET LOCAL app.current_user_id = :uid"),
        {"uid": current_user.id}
    )
    yield db
```

`SET LOCAL` scopes to the current transaction only — automatically cleared
when the connection returns to the pool. No cross-request leak.

**Admin bypass**: Alembic migration role gets `BYPASSRLS`. `reset_password.py`
sets `SET row_security = off` or runs as superuser.

**Tables without `user_id`** (`fx_rates`, `corporate_actions`): shared
read-only reference data — no RLS needed.

**Trade-off**: ~1–2% per-query overhead. Negligible at current scale. Raw
psql debugging requires `SET app.current_user_id = X` or `BYPASSRLS`.

---

## Decision 3: UUIDs for All Primary Keys on User-Facing Resources

**Problem**: Integer sequential IDs are trivially enumerable. Even with
correct 404 responses, `/trades/1 ... /trades/9999` is a low-effort scan.

**Decision**: All user-facing resource tables use `UUID DEFAULT gen_random_uuid()`
as PK. Internal join tables (`trade_tags`, `trade_playbooks`) may keep integer
PKs — users never address them directly.

Migration needed for any remaining integer PK tables. New tables in
`simplified-execution-model` use UUIDs from the start.

---

## Decision 4: Ownership Tests as a First-Class Test Pattern

**Problem**: IDOR vulnerabilities are introduced silently — a new endpoint
without a `user_id` filter has no compile-time warning. Only a test catches it.

**Decision**: A canonical `other_user` + `other_users_<resource>` fixture pair
in `conftest.py`. Every resource endpoint (`GET`, `PATCH`, `DELETE`) gets one
ownership test asserting `404`.

```python
# conftest.py
@pytest.fixture
def other_user(db):
    user = User(email="other@example.com", hashed_password="x")
    db.add(user); db.flush(); return user

@pytest.fixture
def other_users_trade(db, other_user, account):
    trade = Trade(user_id=other_user.id, account_id=account.id, symbol="SPY")
    db.add(trade); db.flush(); return trade

# test_trade_ownership.py
class TestTradeOwnership:
    def test_get_returns_404(self, client, auth_headers, other_users_trade):
        r = client.get(f"/api/v1/trades/{other_users_trade.id}", headers=auth_headers)
        assert r.status_code == 404   # not 403 — no existence leak

    def test_patch_returns_404(self, client, auth_headers, other_users_trade):
        r = client.patch(f"/api/v1/trades/{other_users_trade.id}",
                         json={"symbol": "X"}, headers=auth_headers)
        assert r.status_code == 404

    def test_delete_returns_404(self, client, auth_headers, other_users_trade):
        r = client.delete(f"/api/v1/trades/{other_users_trade.id}", headers=auth_headers)
        assert r.status_code == 404
```

**Coverage target**: GET/PATCH/DELETE for Trades, Executions, Accounts,
Playbooks, Tags, Notes, Screenshots, BrokerRawTransactions = **24 ownership
tests minimum**.

---

## Decision 5: DB-Backed OTT Blocklist

**Problem**: `_used_ott_jti: set[str]` lives in process memory. Process A
marks a JTI as used; Process B has no knowledge of it and accepts the same
token again.

**Decision**: Store used JTIs in a new table:

```sql
CREATE TABLE used_otts (
    jti         TEXT        PRIMARY KEY,
    expires_at  TIMESTAMPTZ NOT NULL
);
CREATE INDEX ix_used_otts_expires ON used_otts(expires_at);
```

**Check-and-insert** (atomic, handles concurrent requests):

```python
async def consume_ott_jti(jti: str, expires_at: datetime, db: AsyncSession) -> bool:
    """Returns True if JTI was fresh (inserted), False if already used."""
    try:
        db.add(UsedOtt(jti=jti, expires_at=expires_at))
        await db.flush()
        return True
    except IntegrityError:
        await db.rollback()
        return False
```

The PRIMARY KEY constraint on `jti` makes the insert atomic — a duplicate
raises `IntegrityError` which is caught and treated as "already used."
No separate SELECT is needed; no race condition.

**Cleanup**: delete expired rows on every `consume_ott_jti` call:
`DELETE FROM used_otts WHERE expires_at < now()`. Keeps the table small
automatically. Adds one DELETE per OTT consumption — acceptable given OTT
usage frequency (password reset, magic link).

**Migration path**: the existing `_used_ott_jti` set is drained on deploy
(in-memory → empty). Any OTTs issued before deploy with the old code are
short-lived by design; within their TTL, they may replay once on the new
deployment. Acceptable trade-off for a non-breaking migration.

---

## Decision 6: Cursor Pagination — User-ID Guard at Repository Layer

**Problem**: The cursor encodes `(sort_field_value, trade_id)`. If the cursor
is not signed, a user could craft a cursor pointing to another user's trade_id
and receive their data — a classic IDOR.

**Two defences, both implemented**:

**Defence A — User-scoped WHERE clause (mandatory)**:
Every repository method that decodes a cursor MUST include
`AND trades.user_id = :current_user_id` in the WHERE clause. The cursor value
only provides the keyset continuation point; ownership is enforced separately.
Even with a manipulated cursor the query returns no rows for the wrong user.

```python
# Before (vulnerable if user_id not always in filters)
WHERE (pnl, id) < (:cursor_pnl, :cursor_id)

# After (safe regardless of cursor value)
WHERE user_id = :uid
  AND (pnl, id) < (:cursor_pnl, :cursor_id)
```

**Defence B — HMAC-signed cursors (added on top)**:
Cursors are base64-encoded JSON signed with `HMAC-SHA256` using the
application's `SECRET_KEY`. A tampered cursor fails signature verification
before the SQL query runs — returns `400 Bad Request`.

```python
import hmac, hashlib, base64, json

def encode_cursor(payload: dict, secret: str) -> str:
    data = json.dumps(payload, separators=(',', ':'))
    sig = hmac.new(secret.encode(), data.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{data}.{sig}".encode()).decode()

def decode_cursor(token: str, secret: str) -> dict:
    raw = base64.urlsafe_b64decode(token.encode()).decode()
    data, sig = raw.rsplit('.', 1)
    expected = hmac.new(secret.encode(), data.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        raise ValueError("Invalid cursor signature")
    return json.loads(data)
```

Defence A alone is sufficient for correctness. Defence B adds tamper evidence
and early rejection. Both are implemented.

---

## Decision 7: CLI Password via `getpass`

**Problem**: `-p <password>` appears in:
- `ps aux` output (readable by all local users)
- `~/.bash_history` / `~/.zsh_history`
- systemd journal / audit log

**Decision**: Remove `-p/--password` argument. Use `getpass.getpass()` for
interactive input, and support pipe input for non-interactive (CI/scripts):

```python
import getpass, sys

if sys.stdin.isatty():
    password = getpass.getpass("New password: ")
    confirm  = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Passwords do not match.", file=sys.stderr)
        sys.exit(1)
else:
    # Non-interactive: read from stdin pipe (e.g. echo "pw" | reset_password.py -u user)
    password = sys.stdin.readline().rstrip('\n')
```

This keeps scripting possible without exposing the password in process args.

---

## Decision 8: Narrow Exception Handling in `security.py`

**Change**: Replace `except (JWTError, ValueError, Exception)` with
`except (JWTError, ValueError)`.

A bare `except Exception` after specific exception types swallows all
unexpected errors — AttributeError, TypeError, bugs — and converts them into
silent auth failures. These should propagate as 500s and appear in logs.

**One legitimate exception** (`database.py`): `except Exception` blocks that
immediately re-raise after a `session.rollback()` are correct and must keep
a clarifying comment: `# Re-raise after rollback — caller sees original exception`.

---

## Risks & Trade-offs

| Risk | Mitigation |
|---|---|
| OTTs issued before deploy may replay once during TTL window | OTT TTL is short (15–60min); acceptable for non-breaking migration |
| `used_otts` table grows if cleanup fails | INDEX on `expires_at`; cleanup runs on every consumption; table stays tiny |
| HMAC cursor signing adds latency | One `hmac.new()` call per request — microseconds, not measurable |
| Non-interactive `reset_password.py` via stdin still visible in bash history | Document: use `read -s pw && echo $pw \| reset_password.py -u user` to avoid history |
