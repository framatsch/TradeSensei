# Schwab CLI

Use `tools/schwab_cli.py` to download Schwab accounts, positions, and trade
transactions into the wrapped JSON format that Trade Sensei imports.

## Required Environment Variables

- `SCHWAB_APP_KEY`
- `SCHWAB_APP_SECRET`
- `SCHWAB_CALLBACK_URL` (optional, defaults to `https://127.0.0.1`)

Set these in a `.env` next to the tool (`tools/.env`) or in the project root
`.env`. The tool also depends on `schwabdev` and `rich`:

```bash
pip install schwabdev rich python-dotenv
```

## Subcommands

```bash
python tools/schwab_cli.py accounts
python tools/schwab_cli.py positions      [--account <number>] [--output <path>]
python tools/schwab_cli.py transactions   [--account <number>] [--start YYYY-MM-DD] [--end YYYY-MM-DD] [--output <path>]
python tools/schwab_cli.py refresh
```

- `accounts` — list all linked Schwab accounts (number + hash).
- `positions` — fetch positions **and** transactions and write the wrapped
  import file (default `tools/cache/positions.json`). This is the file you
  import into Trade Sensei.
- `transactions` — fetch TRADE transactions for a date window (default
  `tools/cache/transactions.json`).
- `refresh` — force a full OAuth re-authentication and refresh all tokens.

Arguments:

- `--account` / `-a`: Schwab account number. Required when the linked login has
  multiple accounts.
- `--start` / `--end` (transactions only): date window. Defaults to the last
  90 days ending today.
- `--output` / `-o`: output file path.

## Account Selection Rules

- If one linked account exists and `--account` is omitted, the tool
  auto-selects it.
- If multiple linked accounts exist and `--account` is omitted, the tool exits
  non-zero and lists available account numbers.
- If `--account` is provided but does not match a linked account, the tool
  exits non-zero and lists available account numbers.

## How open positions are imported

**Open positions are surfaced by the importer from your transactions, not from
the `positions[]` snapshot.** An opening trade with no matching later close is
left as an open lot by the FIFO aggregator — exactly like a stock you bought and
still hold.

This means the **fetched transaction window must include each open position's
opening trade**. If you bought a stock 6 months ago and still hold it, run the
`positions` subcommand (which downloads a 90-day transaction window by default)
only if that purchase is within the window — otherwise fetch a wider window with
the `transactions` subcommand and a suitable `--start`, or re-run once your open
positions' opening trades fall inside the window. Positions whose opening trade
predates the window will **not** appear as open trades after import.

The `positions[]` array is still written to the file for diagnostics, but the
importer does not parse it.

## Output Format

```json
{
  "fetchedAt": "...",
  "accounts": [
    {
      "accountNumber": "...",
      "accountHash": "...",
      "positions": [...],
      "transactions": [...]
    }
  ]
}
```

(The `transactions` subcommand additionally records a top-level `dateRange`.)

## End-to-End Workflow

1. Download data from Schwab:

```bash
python tools/schwab_cli.py positions --account 45302130
```

2. Import into Trade Sensei (example with API):

```bash
curl -X POST \
  "http://localhost:8000/api/v1/imports/upload" \
  -H "Authorization: Bearer <token>" \
  -F "account_id=<tradesensei_account_uuid>" \
  -F "file=@tools/cache/positions.json;type=application/json"
```

The importer reads `accounts[].transactions` and matches the file's
`accountNumber` against the target Trade Sensei account's configured number
(aborting on mismatch or ambiguity).
