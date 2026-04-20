# Split-aware execution linking guide

This guide explains how split-aware execution linking works after broker import, how to troubleshoot lineage issues, and how to deploy or roll back the change safely.

## API behavior for split executions

Endpoint: `GET /api/v1/trades/{trade_id}/executions`

- Auth required: yes (Bearer token)
- Default behavior: returns non-deleted execution legs linked to the trade
- Optional query: `include_deleted=true` to include soft-deleted rows (useful for debugging lineage)

When one imported execution is used by multiple aggregated trades, the backend:

1. Soft-deletes the original execution row
2. Creates child rows with `origin="split"`
3. Sets `parent_id` on each child to the original execution ID
4. Assigns each child to exactly one trade via `trade_id`

Response fields to rely on:

- `origin`: `"split"` for split children
- `parent_id`: UUID of the original imported execution
- `deleted`: `false` on active children, `true` on original row

Example response (single split leg):

```json
{
  "data": [
    {
      "id": "5aa5f8d7-31d9-4a0d-8c83-6942d9a58214",
      "user_id": "f7c02852-9f8d-45c2-a0bd-d3cc8463f117",
      "account_id": "13764557-fdb6-43df-a36d-2d3a26f03dd1",
      "symbol": "AAPL",
      "direction": "LONG",
      "quantity": "60.00000000",
      "price": "243.19000000",
      "commission": "0.60000000",
      "executed_at": "2024-07-01T10:00:00Z",
      "pnl": null,
      "pnl_eur": null,
      "multiplier": 1,
      "currency": "USD",
      "origin": "split",
      "deleted": false,
      "user_modified": false,
      "parent_id": "df1a5908-3520-495f-aa8a-20d339f56c7a",
      "trade_id": "0d11e4f0-4914-4f9a-9a07-fb7e44ff61b8",
      "created_at": "2026-04-19T09:10:00Z",
      "updated_at": "2026-04-19T09:10:00Z"
    }
  ]
}
```

## What users see after import

After import, execution legs are linked to trades automatically.

- A normal one-to-one execution keeps `origin="imported"`
- A split execution shows one leg per trade with `origin="split"`
- The original imported execution is retained as lineage history (`deleted=true`) and does not appear in normal trade detail views

If a user opens trade details and sees one entry/exit leg per trade, this is expected behavior for split-aware linking.

## Troubleshooting missing or incorrect legs

### Symptom: trade has no execution legs

Checks:

1. Verify import completed without errors in backend logs.
2. Call `GET /api/v1/trades/{trade_id}/executions`.
3. If empty, repeat with `include_deleted=true`.

If only deleted rows are returned, the linking step likely failed before child creation.

### Symptom: quantities do not match trade quantity

Run this query:

```sql
SELECT
  t.id AS trade_id,
  t.quantity AS trade_qty,
  COALESCE(SUM(le.quantity), 0) AS legs_qty
FROM trades t
LEFT JOIN logical_executions le ON le.trade_id = t.id AND le.deleted = false
WHERE t.id = '0d11e4f0-4914-4f9a-9a07-fb7e44ff61b8'
GROUP BY t.id, t.quantity;
```

`trade_qty` and `legs_qty` should match for non-combo trades.

### Symptom: split child exists without parent lineage

Run this query:

```sql
SELECT id, trade_id, parent_id, origin
FROM logical_executions
WHERE origin = 'split' AND parent_id IS NULL;
```

Expected result: zero rows.

## Performance characteristics and monitoring

Split-aware linking adds DB work only for executions that are reused across multiple trades.

Operational targets to watch in staging/production:

- Import runtime increase stays below 20% versus baseline
- Split-heavy imports do not produce sustained DB CPU > 80%
- No steady growth of orphan split children (`origin='split' AND trade_id IS NULL`)

Recommended metrics and alerts:

1. Import duration (p50/p95) by broker and account
2. Number of split children created per import
3. Count of linking errors in logs (`Failed to link execution`)
4. Count of orphan split children after each import

Alert thresholds (starting point):

- p95 import duration > baseline × 1.2 for 15 minutes
- linking errors > 0 in 5-minute window
- orphan split children > 0 after import job completion

## Admin debug guide for lineage issues

Use these queries when debugging parent/child lineage:

```sql
-- 1) Inspect one lineage tree
SELECT id, parent_id, trade_id, origin, deleted, quantity, commission, executed_at
FROM logical_executions
WHERE id = 'df1a5908-3520-495f-aa8a-20d339f56c7a'
   OR parent_id = 'df1a5908-3520-495f-aa8a-20d339f56c7a'
ORDER BY deleted DESC, executed_at, id;

-- 2) Validate quantity conservation across all split parents
SELECT p.id AS parent_id, p.quantity AS parent_qty, SUM(c.quantity) AS child_qty
FROM logical_executions p
JOIN logical_executions c ON c.parent_id = p.id
WHERE c.origin = 'split'
GROUP BY p.id, p.quantity
HAVING p.quantity <> SUM(c.quantity);

-- 3) Find orphan children
SELECT id, parent_id, trade_id, quantity
FROM logical_executions
WHERE origin = 'split' AND deleted = false AND trade_id IS NULL;
```

Expected results:

- Query 2 returns zero rows
- Query 3 returns zero rows after import finalization

## Deployment notes

### Migration plan

No data migration is required for this change.

This behavior applies on new imports. Existing data remains unchanged until users re-import.

### Fresh import guidance for users

Use account fresh-start when users want fully consistent split-aware links for historical data:

1. Open the Import screen.
2. Select account and broker file.
3. Choose fresh-start import.
4. Confirm destructive reset and re-import.
5. Validate trade details: each trade should show its execution legs.

### Rollback procedure

If production issues appear:

1. Roll back application image to previous release.
2. Stop new imports temporarily.
3. Re-run fresh-start import for affected accounts after rollback if trade legs are inconsistent.
4. Re-enable imports.

No schema rollback is needed for this change.

### Monitoring and alerts checklist

- Dashboard panel: import duration p50/p95
- Dashboard panel: split children created per import
- Dashboard panel: linking error count
- Alert: `Failed to link execution` log count > 0
- Alert: orphan split children query returns > 0 rows

### Release notes snippet

```md
### Split-aware execution linking after import

- Imported executions now link to trades with split-aware lineage when one execution feeds multiple trades.
- New execution response lineage fields are now populated consistently in trade execution legs (`origin="split"`, `parent_id`).
- No migration is required. To apply linking to historical account data, run a fresh-start import for that account.
```

---

## Position-based metadata propagation

When a broker import produces multiple trades from the same position (e.g. a partial close splits a 100-share entry into a 60-share open leg and a 40-share closed leg), the resulting trades share a common `position_id` identifier.

### Propagatable fields

Updating any of the following fields on an **open** trade propagates the change to all **open** siblings in the same position:

| Field | Description |
|-------|-------------|
| `playbook_id` | Strategy / playbook associated with the trade |
| `tag_ids` | List of classification tags |
| `notes` | Free-text notes |
| `user_rating` | 1–5 quality rating |

### Propagation rules

1. **Open siblings only** — propagation applies only to trades where `closed_at IS NULL` in the same position. Closed trades are never overwritten by propagation.
2. **Same position_id** — propagation is strictly bounded by `position_id`. Two trades with the same symbol but different `position_id` values are never affected by each other's updates.
3. **Last-write-wins** — if a sibling trade was independently edited more recently than the source trade (i.e. `sibling.updated_at > source_trade.updated_at`), it is skipped. This prevents an older edit from overwriting a newer one in concurrent scenarios.
4. **No cross-user leakage** — `user_id` is always part of the propagation query. Another user's trades are never affected.

### Propagation boundary diagram

```
Position A (AAPL)
├── Trade 1 (open)   ← user edits playbook → propagates to Trade 2
├── Trade 2 (open)   ← receives update (if updated_at <= Trade 1.updated_at)
└── Trade 3 (closed) ← never touched by propagation

Position B (AAPL)   ← entirely separate; no propagation from Position A
└── Trade 4 (open)  ← NOT affected even though same symbol
```

### Conflict resolution for concurrent edits

When two users (or two browser tabs) edit different trades in the same position simultaneously:

- Each write records its own `updated_at` timestamp in the database.
- A propagation from Trade A will only overwrite Trade B if `Trade B.updated_at <= Trade A.updated_at`.
- If Trade B was edited **after** Trade A, it is skipped — Trade B's value wins.
- This is a deterministic last-write-wins strategy applied at the SQL level.

**Example:**

```
T=0: Trade A edited (playbook=P1) → propagates to Trade B (P1 written, B.updated_at set to T=0)
T=1: Trade B edited independently (playbook=P2) → B.updated_at set to T=1
T=2: Trade A edited again (playbook=P1) → B.updated_at (T=1) > A.updated_at (T=2 before write)
     propagation guard: B is skipped → B keeps P2
```

### Known edge cases

| Scenario | Behavior |
|----------|----------|
| Trade closed between propagation check and write | Propagation misses it — acceptable; closed trades should not receive propagation anyway |
| position_id not set on trade | Propagation is skipped; field is null-safe |
| Editing a closed trade | No propagation is triggered (service checks `should_propagate` only on update) |
| Large position with many open siblings (>100 trades) | Bulk SQL UPDATE is used; no N+1 risk |
| Tags replaced vs. appended | `tag_ids` propagation replaces the sibling's full tag list with the source's list |

### Audit log events

Successful propagation emits an info-level log line (not an audit event):

```
trade_metadata.propagated user_id=<uuid> trade_id=<uuid> position_id=<uuid> fields=['playbook_id'] siblings=2
```

This is logged at `INFO` level. Check application logs when diagnosing unexpected propagation behavior.

### API response fields

`TradeRead` now includes:

| Field | Type | Description |
|-------|------|-------------|
| `position_id` | `uuid \| null` | Shared position identifier for split-derived trades |
| `user_rating` | `integer(1-5) \| null` | User quality rating for this trade |
