# Concurrent imports validation runbook

This runbook validates concurrent user import behavior for split-aware linking.

## Preconditions

- Backend healthy and connected to DB.
- At least 3 test users/accounts with valid tokens.

## Parallel import command template

```bash
mkdir -p openspec/changes/trade-execution-split-aware-linking/validation/artifacts

(
  curl -sS -X POST "http://localhost:8000/api/v1/imports/ibkr" \
    -H "Authorization: Bearer ${TOKEN_USER_A}" \
    -F "account_id=${ACCOUNT_A}" \
    -F "file=@tests/test_data/ibkr/TraderJournal_anonymized_combined.xml" \
    > openspec/changes/trade-execution-split-aware-linking/validation/artifacts/concurrent-a.json
) &

(
  curl -sS -X POST "http://localhost:8000/api/v1/imports/ibkr" \
    -H "Authorization: Bearer ${TOKEN_USER_B}" \
    -F "account_id=${ACCOUNT_B}" \
    -F "file=@tests/test_data/ibkr/TraderJournal_anonymized_combined.xml" \
    > openspec/changes/trade-execution-split-aware-linking/validation/artifacts/concurrent-b.json
) &

(
  curl -sS -X POST "http://localhost:8000/api/v1/imports/ibkr" \
    -H "Authorization: Bearer ${TOKEN_USER_C}" \
    -F "account_id=${ACCOUNT_C}" \
    -F "file=@tests/test_data/ibkr/TraderJournal_anonymized_combined.xml" \
    > openspec/changes/trade-execution-split-aware-linking/validation/artifacts/concurrent-c.json
) &

wait
```

## Post-run checks

1. Confirm each response reports successful import.
2. Run SQL checks from `../sql/split_integrity_checks.sql` per account.
3. Confirm no orphan split children are left.
