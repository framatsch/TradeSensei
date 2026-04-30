# Database resource usage validation runbook

This runbook validates DB resource behavior under split-aware import load.

## 1) Capture container resource stats during import

```bash
docker stats --no-stream \
  > openspec/changes/trade-execution-split-aware-linking/validation/artifacts/docker-stats-before.txt

# Run split-heavy import in another terminal (see production-volume-import.md)

docker stats --no-stream \
  > openspec/changes/trade-execution-split-aware-linking/validation/artifacts/docker-stats-after.txt
```

## 2) Collect DB activity snapshots

```bash
docker exec tradesensei-db-1 psql -U postgres -d tradesensei \
  -c "SELECT now(), state, wait_event_type, wait_event, query FROM pg_stat_activity WHERE datname='tradesensei';" \
  > openspec/changes/trade-execution-split-aware-linking/validation/artifacts/pg-stat-activity.txt
```

## 3) Run split integrity SQL checks

```bash
docker exec -i tradesensei-db-1 psql -U postgres -d tradesensei \
  < openspec/changes/trade-execution-split-aware-linking/validation/sql/split_integrity_checks.sql \
  > openspec/changes/trade-execution-split-aware-linking/validation/artifacts/split-integrity-query-results.txt
```

## Pass criteria

- No quantity conservation failures.
- No commission conservation failures.
- No split children with null parent.
- No unexpected orphan split children post-import.
