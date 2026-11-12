# Generic CSV import examples

These CSV files are **1:1 conversions of the existing sample data** in
`tests/test_data/ibkr/` and `tests/test_data/schwab/` into the
[Trade Sensei Execution Format v1](../../../docs/import-generic-format.md).
No fills, timestamps, prices or IDs were invented.

| Generic CSV | Source | Executions |
|---|---|---|
| `ibkr/TraderJournal_anonymized_combined.csv` | `ibkr/TraderJournal_anonymized_combined.xml` | 339 |
| `ibkr/combo_positions.csv` | `ibkr/combo_positions.xml` | 16 |
| `schwab/schwab_aggregation.csv` | `schwab/schwab_aggregation.json` | 7 |
| `schwab/schwab_short_roundtrip.csv` | `schwab/schwab_short_roundtrip.json` | 2 |
| `schwab/schwab_transactions_real_trimmed.csv` | `schwab/schwab_transactions_real_trimmed.json` | 5 |

The converter uses the output of the native IBKR/Schwab parsers, so rows the
native import rejects stay out of the CSV (for example the `ZERO_TEST` trade with
quantity zero in the IBKR journal). The native broker transaction ID becomes
`external_id`, so every file uses the `external_id` strategy.

## Manual test

1. Create an **Other broker (generic file)** account in a test portfolio.
2. Preview and upload one of the CSV files.
3. Compare the resulting trades with an IBKR/Schwab account that imported the
   matching source file. Both must show the same trades, executions, quantities,
   prices, commissions, P&L and open/closed state.
4. Upload the same CSV again: the preview must show every execution as already
   imported, and nothing is written.

Use a dedicated test portfolio so the demo trades do not end up in a real journal.
CSV cannot carry stock splits; none of these samples contains one.

## Automated checks

From `backend/`:

```bash
uv run pytest tests/unit/test_generic_import_docs.py -q
uv run pytest tests/integration/test_generic_import.py -k manual_csv -q
```

The unit test regenerates each CSV from its source file and requires it to match
byte for byte, so the samples cannot drift from the IBKR/Schwab data. The
integration test imports the source natively and the CSV into a generic account,
then requires the same economic result and a no-op re-import. Integration tests
need a migrated test database configured via `DATABASE_URL`; never point them at a
production database.
