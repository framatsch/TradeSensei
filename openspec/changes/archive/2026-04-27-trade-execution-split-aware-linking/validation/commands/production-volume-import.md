# Production-like volume validation commands

Use these commands to validate split-aware linking on production-like import volume.

## Preconditions

- Backend service is healthy (`docker compose ps` shows `backend` healthy).
- Test user and account exist.
- JWT token is available as `TOKEN`.

## 1) Baseline import (without split-heavy file)

```bash
time curl -X POST "http://localhost:8000/api/v1/imports/ibkr" \
  -H "Authorization: Bearer ${TOKEN}" \
  -F "account_id=11111111-1111-1111-1111-111111111111" \
  -F "file=@tests/test_data/ibkr/TraderJournal_anonymized_combined.xml"
```

Save output:

```bash
mkdir -p openspec/changes/trade-execution-split-aware-linking/validation/artifacts
time curl -X POST "http://localhost:8000/api/v1/imports/ibkr" \
  -H "Authorization: Bearer ${TOKEN}" \
  -F "account_id=11111111-1111-1111-1111-111111111111" \
  -F "file=@tests/test_data/ibkr/TraderJournal_anonymized_combined.xml" \
  > openspec/changes/trade-execution-split-aware-linking/validation/artifacts/import-baseline.json \
  2> openspec/changes/trade-execution-split-aware-linking/validation/artifacts/import-baseline.time.txt
```

## 2) Split-heavy import run

```bash
time curl -X POST "http://localhost:8000/api/v1/imports/ibkr" \
  -H "Authorization: Bearer ${TOKEN}" \
  -F "account_id=11111111-1111-1111-1111-111111111111" \
  -F "file=@tests/test_data/ibkr/TraderJournal_anonymized_combined.xml" \
  > openspec/changes/trade-execution-split-aware-linking/validation/artifacts/import-split-aware.json \
  2> openspec/changes/trade-execution-split-aware-linking/validation/artifacts/import-split-aware.time.txt
```

## 3) Idempotency re-import check

Re-run fresh-start import twice and compare normalized outputs:

```bash
curl -X POST "http://localhost:8000/api/v1/imports/ibkr" \
  -H "Authorization: Bearer ${TOKEN}" \
  -F "account_id=11111111-1111-1111-1111-111111111111" \
  -F "file=@tests/test_data/ibkr/TraderJournal_anonymized_combined.xml" \
  > openspec/changes/trade-execution-split-aware-linking/validation/artifacts/idempotency-run-1.json

curl -X POST "http://localhost:8000/api/v1/imports/ibkr" \
  -H "Authorization: Bearer ${TOKEN}" \
  -F "account_id=11111111-1111-1111-1111-111111111111" \
  -F "file=@tests/test_data/ibkr/TraderJournal_anonymized_combined.xml" \
  > openspec/changes/trade-execution-split-aware-linking/validation/artifacts/idempotency-run-2.json
```

Then compare business-level equivalence (counts + sum checks via SQL in `../sql/split_integrity_checks.sql`).

## 4) API functionality spot check

```bash
curl -sS "http://localhost:8000/api/v1/trades/${TRADE_ID}/executions" \
  -H "Authorization: Bearer ${TOKEN}" \
  > openspec/changes/trade-execution-split-aware-linking/validation/artifacts/trade-executions-${TRADE_ID}.json
```

Pass criteria:

- Endpoint returns at least one leg for split-aware scenarios.
- Split children include `origin="split"` and non-null `parent_id`.
