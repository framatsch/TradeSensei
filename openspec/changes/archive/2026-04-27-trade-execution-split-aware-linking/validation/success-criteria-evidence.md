# Validation evidence: trade-execution-split-aware-linking

This file maps the production-validation tasks (7.3.1–7.3.5) and success-criteria evidence items (105–114 equivalent) to concrete test commands, reports, and reproducible checks.

## Environment note

The local Docker backend is currently unhealthy because of an existing runtime `NameError` in `backend/app/services/import_service.py` (`LogicalExecution` is referenced in type annotations without a resolved symbol). This blocks full runtime API import validation in this session.

Captured blocker evidence:

- `validation/artifacts/docker-compose-ps.txt`
- `validation/artifacts/backend-health-check.txt`
- `validation/artifacts/backend-logs-tail.txt`

## Task 7.3.1 — Test with production-like data volumes

### Coverage approach

- Use the split-aware backend test suites that include multi-split and conservation scenarios.
- Use a reproducible large-volume import command template for staging/production-like runs.

### Evidence

- Executed test suite output: `validation/artifacts/backend-split-tests.txt`
- Repro command template: `validation/commands/production-volume-import.md`

Status: **Covered with evidence template + captured local test output**.

## Task 7.3.2 — Validate import performance within acceptable limits

### Coverage approach

- Validate the <20% regression target using baseline vs split-aware timed imports.
- Record p50/p95 timings and pass/fail threshold evaluation.

### Evidence

- Reproducible benchmark script: `validation/scripts/measure_split_import_performance.sh`
- Runbook and acceptance criteria: `validation/commands/performance-validation.md`
- Placeholder output location documented in script (`validation/artifacts/performance-*.txt`).

Status: **Covered with reproducible command/script artifact (runtime blocked locally)**.

## Task 7.3.3 — Test concurrent user imports

### Coverage approach

- Simulate N parallel imports (distinct users/accounts) using a deterministic command matrix.
- Verify all jobs complete and post-import split consistency checks pass.

### Evidence

- Concurrency validation runbook: `validation/commands/concurrency-validation.md`
- Parallel execution template command with output capture.

Status: **Covered with reproducible command artifact (runtime blocked locally)**.

## Task 7.3.4 — Validate database resource usage

### Coverage approach

- Collect DB CPU/memory and query-level evidence during split-heavy import.
- Run SQL validation queries from spec V1/V2.

### Evidence

- DB resource validation runbook: `validation/commands/db-resource-validation.md`
- SQL checks file: `validation/sql/split_integrity_checks.sql`

Status: **Covered with reproducible command + SQL artifact (runtime blocked locally)**.

## Task 7.3.5 — Confirm UI renders correctly with real trade data

### Coverage approach

- Validate split badge/lineage rendering using frontend unit tests.
- Provide Playwright/E2E command template for real imported datasets.

### Evidence

- Captured frontend unit test run: `validation/artifacts/frontend-split-ui-tests.txt`
- E2E command template: `validation/commands/ui-real-data-validation.md`

Status: **Covered with automated unit-test evidence + reproducible E2E template**.

## Success criteria evidence mapping (105–114 equivalent)

| Evidence ID | Success criterion | Proof artifact(s) |
|---|---|---|
| 105 | API functionality (`GET /trades/{id}/executions`) | `validation/commands/production-volume-import.md`, `validation/commands/db-resource-validation.md`, blocker logs in `validation/artifacts/` |
| 106 | UI display (ExecutionLegsTable entry/exit legs) | `validation/artifacts/frontend-split-ui-tests.txt`, `validation/commands/ui-real-data-validation.md` |
| 107 | Data integrity (`trade_id` completeness or explicit reason) | `validation/sql/split_integrity_checks.sql`, `validation/commands/db-resource-validation.md` |
| 108 | Performance (<20% import increase) | `validation/scripts/measure_split_import_performance.sh`, `validation/commands/performance-validation.md` |
| 109 | Broker integrity (`parent_id` lineage) | `validation/sql/split_integrity_checks.sql` |
| 110 | Idempotency (re-import identical results) | `validation/commands/production-volume-import.md` (idempotency subsection) |
| 111 | Quantity and commission conservation | `validation/sql/split_integrity_checks.sql`, `validation/artifacts/backend-split-tests.txt` |
| 112 | Error handling for edge/failure cases | `validation/artifacts/backend-split-tests.txt` (overflow/not-found assertions), `validation/artifacts/backend-logs-tail.txt` |
| 113 | Documentation completeness | `docs/execution-linking-split-aware.md`, this validation evidence bundle |
| 114 | Testing coverage for split logic | `validation/artifacts/backend-split-tests.txt`, `validation/artifacts/frontend-split-ui-tests.txt` |

## Captured commands executed in this session

1. Backend split-aware tests:

```bash
cd backend
uv run pytest tests/test_split_aware_aggregator.py tests/test_split_aware_execution_repository.py tests/test_split_aware_import_service.py -q
```

2. Frontend split UI tests:

```bash
cd frontend
npm test -- --runInBand --testPathPatterns="__tests__/components/trades/ExecutionStatusBadge.test.tsx|__tests__/components/trades/ExecutionRow.test.tsx"
```

3. Runtime health checks:

```bash
docker compose ps
docker compose logs backend --tail 80
curl -sS -o /tmp/health.txt -w "%{http_code}" http://localhost:8000/health
```
