## Context

The current ownership hierarchy is `User → Account → Trade`. Every account
belongs directly to a user; trades can be filtered by `account_id` but there
is no layer between user and account that enforces data separation, currency
context, or paper/live trading boundaries.

Three concrete problems this creates:

1. **No live/paper isolation**: A user can mix live trades and paper trades in
   the same analytics view. There is no server-enforced boundary preventing
   cross-contamination.
2. **No base-currency context**: Aggregated PnL figures are produced in mixed
   currencies; the EUR conversion path (Bundesbank) is a workaround rather
   than a first-class feature.
3. **No scalable multi-account view**: A user with five accounts has no way to
   group accounts into a named "portfolio" for aggregate reporting.

This design introduces `Portfolio` as a new entity sitting between `User` and
`Account`. It is intentionally minimal — the scope is the data model and API
isolation only. Currency conversion logic is *not* implemented in this
iteration; the `base_currency` field is stored and plumbed, but cross-currency
arithmetic is deferred to a later spec.

---

## Goals / Non-Goals

**Goals:**

- Define the `Portfolio` ORM model and DB table with all required columns.
- Add `portfolio_id` FK to `accounts` (non-nullable post-migration).
- Write the Alembic migration with data backfill (one default portfolio per
  existing user → link all their accounts to it).
- Expose full CRUD endpoints for portfolios (`GET/POST/PATCH/DELETE`).
- Enforce portfolio ownership on all scoped read/write endpoints:
  - Trades, executions, metrics, timeseries, cash-transactions, imports.
  - Cross-portfolio or missing portfolio access returns `HTTP 403 / 404`.
- Extend existing Row-Level Security (RLS) policy to cover the new table.

**Non-Goals:**

- Frontend changes (separate spec).
- Cross-currency PnL conversion arithmetic (deferred — `base_currency` is
  stored and validated but not yet used for computation).
- Portfolio-to-portfolio transfer operations.
- Sharing portfolios between users.
- Portfolio-level statistics/aggregation dashboard endpoint (out of scope
  for this iteration; existing metrics endpoints become portfolio-scoped as a
  side-effect of isolation).

---

## Decisions

### D1: Portfolio as a new top-level entity (not a tag/group on Account)

**Chosen**: New `portfolios` table with `id`, `user_id`, `name`, `base_currency`,
`color_hex`, `created_at`, `updated_at`.

**`is_paper` removed**: Originally proposed as a live/paper flag on the Portfolio.
Removed because the existing Account model has no `is_paper` field and the backend
enforces no separation between live and paper trades anywhere. Adding `is_paper`
as a pure UI label with no technical enforcement would be misleading — it would
suggest a guarantee the system cannot provide. If live/paper isolation is needed
in the future it should be designed properly (Account-level flag + enforcement).

**Alternatives considered**:
- *Add `base_currency` directly to Account* — rejected: does not solve aggregate
  grouping; two accounts in the same portfolio would have to duplicate the
  currency setting with no enforcement.
- *Use a JSON settings blob on Account* — rejected: untyped, no FK integrity,
  no clean query path for isolation.

**Rationale**: A separate entity models the domain correctly. The cost
(one new table, one FK) is low; the correctness benefit is high.

---

### D2: `portfolio_id` on Account is non-nullable

**Chosen**: After migration, `portfolio_id` is `NOT NULL` with a FK constraint.

**Alternatives considered**:
- *Nullable portfolio_id* — allows gradual adoption but permanently weakens
  isolation guarantees. Any null-portfolio account becomes a silent data
  quality hole.

**Rationale**: Invariant is best enforced by the DB schema. The migration
handles every existing account by assigning it to a default portfolio, so
there is no legitimate null case post-migration.

**Risk**: If the migration fails mid-way, a partial state can leave the
`portfolio_id` column added but not yet populated. Mitigation: migration runs
in a single transaction; if it fails, the column addition rolls back with it.

---

### D3: One default portfolio created per user during migration

**Chosen**: Migration iterates all existing users, creates
`"Default Portfolio"` for each, sets `base_currency = 'USD'` (the
most common existing account currency), `is_paper = false`, and assigns all of
that user's accounts to it.

**Alternatives considered**:
- *Single global default portfolio* — nonsensical for a multi-user system.
- *Infer currency from the majority of user's account currencies* — adds
  migration complexity for marginal benefit; user can rename and reconfigure
  after migration.

**Rationale**: Safest, least-disruptive option. `base_currency` can be changed
by the user until the first trade is present (see D5). `is_paper` is not set
in the migration because the field has been removed from the model.

---

### D4: `portfolio_id` is passed as a path segment, not a query parameter

**Chosen**: Portfolio-scoped endpoints follow the pattern
`/portfolios/{portfolio_id}/trades`, `/portfolios/{portfolio_id}/metrics`, etc.

**Alternatives considered**:
- *`?portfolio_id=` query param on existing endpoints* — cheaper to implement
  but exposes ambiguity (what happens when param is absent? silently returns
  all user data). Path segment makes the scope explicit and mandatory.
- *Header-based portfolio context* — invisible, harder to test, not idiomatic
  REST.

**Rationale**: Path-segment scoping is standard REST practice. It is also
aligned with how the existing `account_id` path param works on
`/accounts/{account_id}/cash-transactions`.

**Breaking change**: All existing clients must update their base paths.
Frontend migration is a separate workstream.

---

### D5: `base_currency` is immutable once portfolio has linked trades

**Chosen**: `PATCH /portfolios/{portfolio_id}` rejects `base_currency` changes
with `HTTP 422` if the portfolio has any associated trades.

**Alternatives considered**:
- *Allow change at any time and recompute historic PnL* — deferred; currency
  conversion arithmetic is out of scope for this spec.
- *Never allow change* — overly restrictive for the initial setup phase.

**Rationale**: Prevents silent data corruption without blocking legitimate
setup-phase reconfiguration.

---

### D6: Portfolio isolation enforced in the repository layer, not middleware

**Chosen**: Each repository method that scopes to trades/executions/cash
takes `portfolio_id` as an explicit parameter and adds a JOIN/subquery to
verify the FK chain: `trade.account.portfolio_id = portfolio_id AND
portfolio.user_id = current_user_id`.

**Alternatives considered**:
- *Middleware that reads `portfolio_id` from path and sets a request-scoped
  context variable* — simpler surface area but relies on every query correctly
  reading the context; hard to audit and easy to miss on new endpoints.
- *DB-level RLS policy on `portfolio_id`* — most robust, but TimescaleDB
  hypertable RLS has known caveats and our existing RLS layer is already
  user-scoped; adding a second dimension risks unforeseen interactions.

**Rationale**: Repository-layer enforcement is explicit, testable, and
consistent with the existing pattern (every repo method already accepts
`user_id`). The service layer becomes the single authoritative point for
constructing the (user_id, portfolio_id) tuple.

---

### D7: `color_hex` stored as 7-char string `#RRGGBB`

**Chosen**: `VARCHAR(7)` with a `CHECK` constraint
`(color_hex ~ '^#[0-9A-Fa-f]{6}$')`.

**Rationale**: Consistent with the existing `Tag.color` column convention.
No ORM-level validator needed; DB rejects invalid values.

---

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| Migration failure on large user base | Migration runs in a single transaction; tested locally against production-size seed before deployment. |
| Existing API clients break (path change) | Coordinated with frontend team; old paths will return `HTTP 410 Gone` with a deprecation message for one release cycle. |
| `base_currency` immutability UX friction | UI shows a warning when currency change is blocked; links to a "how to fix" guide. |
| EUR conversion still computed even though `base_currency` may differ | Bundesbank EUR path remains active; `base_currency` is stored but not yet driving computation — this is a known and documented limitation for this iteration. |
| New portfolio endpoints increase attack surface | Ownership check is always the first operation in every portfolio service method; unauthorized access returns `HTTP 404` (not 403) to avoid information disclosure. |
| Trade queries with extra JOIN may regress performance | `portfolio_id` index added on `accounts`; query plan verified in local TimescaleDB. |

---

## Migration Plan

### Step 1 — Schema change (additive)
```sql
CREATE TABLE portfolios (...);
ALTER TABLE accounts ADD COLUMN portfolio_id UUID NULLABLE REFERENCES portfolios(id);
CREATE INDEX ix_accounts_portfolio_id ON accounts(portfolio_id);
```

### Step 2 — Data backfill
```sql
-- For each user, create one default portfolio and link their accounts
INSERT INTO portfolios (id, user_id, name, base_currency, is_paper, color_hex, ...)
SELECT gen_random_uuid(), id, 'Default Portfolio', 'USD', false, '#6366f1', now(), now()
FROM users;

UPDATE accounts a
SET portfolio_id = p.id
FROM portfolios p
WHERE p.user_id = a.user_id;
```

### Step 3 — Enforce NOT NULL constraint
```sql
ALTER TABLE accounts ALTER COLUMN portfolio_id SET NOT NULL;
```

All three steps run inside a single Alembic migration. No separate "second
migration" is needed. Rollback drops the column (SET NULL renders all three
steps reversible in sequence).

### Rollback
Alembic `downgrade` reverses in order:
1. Drop NOT NULL constraint on `portfolio_id`
2. `UPDATE accounts SET portfolio_id = NULL`
3. Drop `portfolios` table

---

## Resolved Decisions

All open questions are now resolved. No open questions remain.

1. **Default portfolio naming** — **`"Default Portfolio"`** (generic, neutral).
   Username exposure in the UI is avoided. User can rename immediately after
   first login.

2. **`base_currency` validation** — **Fixed allowlist**: `USD`, `EUR`, `GBP`,
   `CHF`, `JPY`, `AUD`, `CAD`. Validated in `PortfolioCreate` and
   `PortfolioUpdate` Pydantic schemas via `Literal` or `Enum`. Backend returns
   HTTP 422 for values outside the allowlist. Allowlist extended in code (no
   migration) when new currencies are needed.

3. **Portfolio deletion semantics** — **Block only, no `force` param**.
   `DELETE /portfolios/{id}` returns HTTP 409 if any accounts are linked.
   There is no cascade or `force=true` option. User must move or delete all
   accounts first. This prevents any accidental data loss via a single API call.

4. **`is_paper` immutability** — **Resolved**: `is_paper` removed from the
   model entirely. No flag, no badge, no enforcement. If live/paper separation
   is needed in the future it must be designed at the Account level with proper
   enforcement.

5. **RLS extension** — **Application-layer only** (D6 confirmed). Repository
   JOINs enforce `portfolio.user_id = current_user_id` on every query. No second
   RLS variable `app.current_portfolio_id` is added — the double-check at the
   repository layer is sufficient and avoids TimescaleDB hypertable RLS
   interaction risks.
