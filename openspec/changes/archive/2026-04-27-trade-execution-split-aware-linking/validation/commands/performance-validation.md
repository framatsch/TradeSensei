# Performance validation runbook

This runbook validates the success criterion: import time increase remains under 20%.

## Command

```bash
bash openspec/changes/trade-execution-split-aware-linking/validation/scripts/measure_split_import_performance.sh
```

## Expected outputs

The script writes:

- `validation/artifacts/performance-baseline.time.txt`
- `validation/artifacts/performance-split.time.txt`
- `validation/artifacts/performance-summary.txt`

## Pass/fail rule

- Pass if `(split_time - baseline_time) / baseline_time <= 0.20`.
- Fail otherwise.

## Notes

- Run at least 3 iterations and use median value when the environment is noisy.
- Keep broker file and account constant between baseline and split runs.
