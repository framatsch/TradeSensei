---
name: db-migration
description: Create, review, and apply Alembic database migrations for the tradesensei backend including TimescaleDB hypertable setup
license: MIT
compatibility: opencode
metadata:
  toolchain: alembic, uv, docker
---

## What I do

Guide the full migration lifecycle: autogenerate, review, apply, and verify —
with special handling for TimescaleDB hypertables and indexes.

## When to use me

- After adding or modifying a SQLAlchemy model in `backend/app/models/`
- When creating a new hypertable for a time-series table
- When troubleshooting migration failures in CI or production

## Prerequisites

```bash
# DB must be running
docker compose up -d db

# Ensure .env is set
DATABASE_URL=postgresql+asyncpg://tradesensei:tradesensei@localhost:5432/tradesensei
```

## Step-by-step workflow

### 1. Make model changes

Edit files in `backend/app/models/`. Never alter the DB directly.

### 2. Generate the migration

```bash
cd backend/
uv run alembic revision --autogenerate -m "add_trades_table"
# Creates: alembic/versions/<hash>_add_trades_table.py
```

### 3. Review the generated migration — ALWAYS

Open the generated file and verify:
- `op.create_table(...)` has all expected columns
- Column types match: use `Numeric(18, 8)` for prices, `DateTime(timezone=True)` for timestamps
- Indexes are created explicitly (not assumed)
- No unintended `DROP COLUMN` or `DROP TABLE` operations

### 4. Add TimescaleDB hypertable (time-series tables only)

After `op.create_table(...)`, add:

```python
op.execute(
    "SELECT create_hypertable('trades', 'closed_at', "
    "chunk_time_interval => INTERVAL '1 month', "
    "if_not_exists => TRUE)"
)
```

Note: `if_not_exists => TRUE` makes the migration idempotent.

### 5. Apply the migration

```bash
uv run alembic upgrade head
```

### 6. Verify

```bash
# Check current revision
uv run alembic current

# Check migration history
uv run alembic history --verbose

# Verify hypertable was created (TimescaleDB)
docker compose exec db psql -U tradesensei -d tradesensei \
  -c "SELECT * FROM timescaledb_information.hypertables;"
```

### 7. Test the downgrade path

```bash
uv run alembic downgrade -1
uv run alembic upgrade head
```

## Migration naming conventions

Use descriptive snake_case names that describe the change:

```
add_trades_table
add_users_accounts_tables
add_account_id_fk_to_trades
add_composite_index_symbol_closed_at
add_pnl_column_to_trades
```

## Rollback procedure

```bash
# Rollback one revision
uv run alembic downgrade -1

# Rollback to specific revision
uv run alembic downgrade <revision_id>

# Show what SQL would run (dry-run)
uv run alembic upgrade head --sql
```

## Common errors

| Error | Cause | Fix |
|-------|-------|-----|
| `Target database is not up to date` | Migration was applied manually | Run `alembic stamp head` carefully |
| `Can't locate revision` | `uv.lock` out of sync | Run `uv sync` first |
| `relation already exists` | Migration ran twice | Add `IF NOT EXISTS` to `op.execute()` |
| `create_hypertable: table must be empty` | Applying hypertable to table with data | Migrate data out first |
