# UI validation with real trade data

This runbook validates frontend rendering of split-aware execution legs against imported data.

## Automated unit baseline (already executable locally)

```bash
cd frontend
npm test -- --runInBand --testPathPatterns="__tests__/components/trades/ExecutionStatusBadge.test.tsx|__tests__/components/trades/ExecutionRow.test.tsx"
```

Expected: all tests pass.

## Real-data UI check with Playwright (manual/e2e)

1. Import real or production-like data first.
2. Open a trade that is known to use split children.
3. Verify ExecutionLegsTable shows:
   - One or more legs
   - Split status badge
   - Lineage indicator (`parent_id`-driven label/tooltip)

Example command:

```bash
npx playwright test tests/e2e/trade-execution-legs.spec.ts --project=chromium
```

Artifact capture target:

- `openspec/changes/trade-execution-split-aware-linking/validation/artifacts/ui-trade-legs-playwright.txt`
- screenshot files under `test-results/`.
