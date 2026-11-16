# Import from other brokers

The **Trade Sensei Execution Format v1** lets you import executions from a broker
without a native Trade Sensei integration. Convert your broker export to JSON or
CSV, create an **Other broker (generic file)** account, and upload the converted
file. Generic accounts accept only this format and do not use API credentials or
remote sync.

Files enter the same import pipeline as native broker exports, including FIFO
matching, option combinations, split adjustments, and protection of journaled
trades. Upload executions (individual fills), not already aggregated trades.

## Choose JSON or CSV

- **JSON** supports executions and stock splits. Its envelope must contain
  `format: "tradesensei.executions"`, a version such as `"1.0"`, and a non-empty
  `executions` array. An optional `source` label is informational, limited to
  100 characters, and never used for identity.
- **CSV** supports executions only. Use UTF-8 (an optional BOM is accepted), a
  comma delimiter, and a header row. Empty cells mean absent values. Quote cells
  according to standard CSV rules. Numbers use a decimal point, **no thousands
  separators**, and no currency symbols.
- Unknown fields or columns are rejected rather than silently ignored.
- Both formats are subject to the application's configured import file-size limit.

Authenticated users can download the current JSON Schema at
`GET /api/v1/imports/formats/generic` and the CSV template at
`GET /api/v1/imports/formats/generic/template.csv`. The import dialog also offers
format help and the template download.

## Execution fields

| Field | Required | Meaning and validation |
|---|---|---|
| `external_id` | No | Unique broker ID for **one fill**, 1–100 characters; surrounding whitespace is trimmed. Either every execution has an ID or none do. |
| `executed_at` | Yes | RFC 3339 timestamp with `Z` or an explicit UTC offset; normalized to UTC. More than 24 hours in the future is rejected. |
| `symbol` | Yes | Instrument ticker, normalized to uppercase. For options, use the **underlying** ticker. |
| `asset_class` | Yes | `EQUITY`, `OPTION`, `FUTURE`, `FOREX`, or `CRYPTO`. |
| `side` | Yes | `BUY` or `SELL`, including buys to close and sells to open. |
| `position_effect` | No | `OPEN`, `CLOSE`, or `CLOSE_OPEN` for a fill that closes and reverses a position. Omit if unknown, but note that a closing fill needs `CLOSE` or a `realized_pnl` value for its trade P&L to be computed. |
| `quantity` | Yes | Absolute quantity greater than zero. Put the buy/sell direction in `side`, not the quantity's sign. |
| `price` | Yes | Non-negative per-unit execution price, before multiplying by the contract multiplier. |
| `commission` | No | Non-negative total fees for this fill, not fees per unit. Defaults to zero. |
| `currency` | Yes | Three-letter uppercase ISO 4217 currency code, such as `USD` or `EUR`. |
| `multiplier` | For options/futures | Integer at least 1. Required for `OPTION` and `FUTURE`; otherwise defaults to 1. |
| `order_id` | No | Order identifier, 1–100 characters, shared by fills or legs of the same order. It is **not** the per-fill ID. |
| `contract_id` | No | Broker contract identifier, 1–50 characters. Supply it when available, especially for futures or adjusted options. |
| `option.strike` | For options | Positive strike price. In CSV: `option_strike`. |
| `option.expiry` | For options | Expiry date in `YYYY-MM-DD` form. In CSV: `option_expiry`. |
| `option.right` | For options | `C` for call or `P` for put. In CSV: `option_right`. |
| `realized_pnl` | No | Broker-reported realized P&L for the execution; informational and may be negative. |

JSON decimals can be numbers or strings. Strings are convenient when exporting
from a spreadsheet or script and preserve decimal precision without binary-float
conversion. The `option` object is required for options and forbidden for other
asset classes. Contract multipliers are not inferred: use your broker's contract
specification, not an assumed value.

### JSON example

This example is a two-fill equity round trip. Each fill has its own external ID.

```json
{
  "format": "tradesensei.executions",
  "version": "1.0",
  "source": "Example broker",
  "executions": [
    {
      "external_id": "fill-1001",
      "executed_at": "2026-01-15T14:30:00Z",
      "symbol": "AAPL",
      "asset_class": "EQUITY",
      "side": "BUY",
      "position_effect": "OPEN",
      "quantity": "10",
      "price": "200.10",
      "commission": "1.00",
      "currency": "USD",
      "order_id": "order-1001"
    },
    {
      "external_id": "fill-1002",
      "executed_at": "2026-01-16T15:00:00Z",
      "symbol": "AAPL",
      "asset_class": "EQUITY",
      "side": "SELL",
      "position_effect": "CLOSE",
      "quantity": "10",
      "price": "205.25",
      "commission": "1.00",
      "currency": "USD",
      "order_id": "order-1002"
    }
  ]
}
```

### CSV example

The following CSV describes the same executions. Optional columns may be omitted.

```csv
external_id,executed_at,symbol,asset_class,side,position_effect,quantity,price,commission,currency,order_id
fill-1001,2026-01-15T14:30:00Z,AAPL,EQUITY,BUY,OPEN,10,200.10,1.00,USD,order-1001
fill-1002,2026-01-16T15:00:00Z,AAPL,EQUITY,SELL,CLOSE,10,205.25,1.00,USD,order-1002
```

For an option fill, add `multiplier`, `option_strike`, `option_expiry`, and
`option_right` columns. Use the underlying symbol, for example `SPY`, rather than
an OCC contract string. Without `contract_id`, option identity is derived from
the underlying, expiry, right, and normalized strike, keeping distinct contracts
separate.

Ready-to-upload CSV files are in [`tests/test_data/generic/`](../tests/test_data/generic/README.md).
They are 1:1 conversions of the IBKR and Schwab sample data in `tests/test_data/`,
so the result can be compared with the native import. The README lists the
sources, a manual test procedure, and the automated checks.

## Stock splits (JSON only)

Add an optional `corporate_actions` array to the JSON envelope. Each entry has
`type: "SPLIT"`, `symbol`, `date` (`YYYY-MM-DD`), and a positive decimal `ratio`.
The ratio is **shares after / shares before**: `"2"` for a two-for-one split,
`"0.1"` for a one-for-ten reverse split. Optional `old_contract_id` and
`new_contract_id` describe a broker contract-ID change at the split.

Generic splits are insert-only. An existing split with the same ratio is
unchanged. A different ratio produces a conflict warning and **does not overwrite**
the stored split, including one imported from another broker. Review conflicts
before confirming an import.

## Identity and safe re-imports

### Prefer broker-provided fill IDs

If your broker supplies stable fill IDs, put them in `external_id` on every row.
Duplicate IDs within a file reject the whole file, even when the rows are otherwise
different. Multiple partial fills belonging to one order must have distinct fill
IDs and may share an `order_id`.

IDs are scoped to the account: the same external ID in two generic accounts does
not collide. Changing `source` does not affect identity. Re-uploading an existing
ID does not replace its original execution; use the application's existing
execution correction or suppression workflow for corrections.

### Files without fill IDs use fingerprints

If the broker has no stable fill IDs, omit `external_id` from **every** row. Trade
Sensei fingerprints UTC execution time (microsecond precision), symbol, asset
class, contract identity, buy/sell side, normalized quantity, normalized price,
and currency. Fees, realized P&L, position effect, and order ID do not affect the
fingerprint. An occurrence number distinguishes otherwise identical partial
fills within a file.

The same file can be imported again without duplicate executions. Overlapping
exports work when identical fills occur the same number of times in their overlap.
**Limitation:** if overlapping files contain different numbers of otherwise
identical fills, occurrence numbering cannot identify which broker fill is which.
Prefer non-overlapping export ranges or stable broker fill IDs, and review the
preview's new/already-imported counts carefully.

**Limitation:** without IDs, fills on the same contract with exactly the same
timestamp have no guaranteed FIFO order: every fill is imported, but which lot a
close is matched against may differ from your broker (for example two buys at
200 and 202 in the same second, partly closed later). If this matters, supply
`external_id` values or timestamps with sub-second precision. Do not invent IDs from spreadsheet
row numbers, which change when exports are reordered or date ranges change.

### The first import locks the account's strategy

The first successful import records either `external_id` or `fingerprint` for the
account. Preview does not set this property. Later uploads using the other
strategy are rejected with `id_strategy_mismatch`, without writing executions.

Use another generic account to maintain a separate history, or use the account's
**clear all trades** action to reset its recorded strategy. Clearing trades is
destructive: do not do it merely to bypass a warning without first checking the
account's history and journal metadata.

## Preview, validation, and confirmation

1. Select a generic account and choose a `.json` or `.csv` file.
2. Preview validates the entire file without writing transactions, trades,
   logical executions, splits, or account properties.
3. Review the detected and recorded ID strategies, total/new/already-imported/
   suppressed execution counts, split conflicts, and warnings.
4. Confirm explicitly to import. Confirmation is disabled for validation errors
   or an ID-strategy conflict.

Validation is all-or-nothing. Errors identify `row`, `field`, `code`, and `message`,
without echoing prices, quantities, or P&L. CSV row numbers start at **1 for the
first data row**, excluding the header; JSON execution indexes start at **0**.
At most 200 errors are returned. Fix the file and preview again. A file cannot mix
rows with and without external IDs.

## Conversion tips and v1 limitations

- **Spreadsheet:** create one row per fill, rename columns to the documented
  names, convert timestamps to offset-aware values, and export comma-delimited
  UTF-8 CSV. Preserve IDs as text so leading zeros are not lost.
- **Script:** map signed quantities to absolute `quantity` plus `side`; make fees
  absolute; preserve per-fill IDs, contract IDs, and order grouping. Serialize
  monetary values using decimal strings.
- **LLM-assisted conversion:** ask for the published schema and one row per fill,
  no invented IDs or data, exact decimal strings, and explicit timezone offsets.
  Remove account numbers and other sensitive information before sharing a broker
  export externally. Always verify the result against the original export and the
  import preview; generated data is not authoritative.
- If `position_effect` is uncertain, omit it rather than guessing. Native FIFO
  rules still apply, including warnings for closing fills without matching opens.
  Trade P&L is computed from prices only for fills marked `CLOSE` or carrying a
  `realized_pnl` value; otherwise closed trades show no P&L.
- Futures without `contract_id` must use symbols that include the contract month
  so different contracts do not match each other.
- v1 does **not** support cash movements, dividends, interest, transfers, or
  broker-specific conversion tools. Splits require JSON. Use complete execution
  history where possible so FIFO has the opening fills needed to match closes.
- Only major version 1 is supported. Unknown fields remain invalid even when
  the version string uses a later `1.x` minor version.
