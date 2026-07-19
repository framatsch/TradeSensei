## ADDED Requirements

### Requirement: Execution legs carry typed option contract fields
The system SHALL store three typed, nullable fields on each execution leg —
`strike` (decimal), `expiry` (date), and `option_type` (`'C'` or `'P'`) — on both the
`logical_executions` and `broker_raw_transactions` tables. For option legs these SHALL be
derived from the OCC symbol during import; for non-option legs and manually created legs
they SHALL be `null`. `option_type` SHALL be constrained to `'C'`, `'P'`, or `null`. The
fields SHALL be included in the `LogicalExecutionRead` API response.

#### Scenario: Imported call option leg exposes strike, expiry, and type
- **WHEN** an IBKR or Schwab file with an option leg whose OCC symbol is `QQQ   251003C00712000` is imported
- **THEN** the persisted leg has `strike = 712.00`, `expiry = 2025-10-03`, and `option_type = "C"`
- **THEN** the leg's `symbol` remains the underlying `"QQQ"`

#### Scenario: Imported put option leg parses type P
- **WHEN** an option leg with OCC symbol `AAPL  260320P00150000` is imported
- **THEN** the persisted leg has `strike = 150.00`, `expiry = 2026-03-20`, and `option_type = "P"`

#### Scenario: Equity leg has null option fields
- **WHEN** an EQUITY leg (e.g. `AAPL`) is imported
- **THEN** the persisted leg has `strike = null`, `expiry = null`, and `option_type = null`

#### Scenario: API response includes the option fields
- **WHEN** a client fetches a trade whose legs include an option contract
- **THEN** each option leg in the response includes `strike`, `expiry`, and `option_type`; non-option legs include the same keys with `null` values

#### Scenario: Invalid option_type is rejected
- **WHEN** a leg record is created with `option_type = "X"`
- **THEN** validation fails with an error stating `option_type` must be `'C'`, `'P'`, or `None`

---

### Requirement: Existing imported option legs are backfilled with contract fields
The system SHALL backfill `strike`, `expiry`, and `option_type` for previously imported
option legs by re-deriving them from the full OCC symbol preserved in the raw transaction's
`raw_data`. Logical execution legs SHALL be backfilled by joining to their originating raw
transaction via `logical_executions.source_id = broker_raw_transactions.id`. Rows whose
`raw_data` symbol is not a valid OCC option string SHALL be left with `null` fields.

#### Scenario: Pre-existing option leg is backfilled after migration
- **WHEN** the migration runs against a database that already contains an imported option leg whose `raw_data` symbol is `QQQ   251003C00712000`
- **THEN** after upgrade the corresponding `logical_executions` and `broker_raw_transactions` rows have `strike = 712.00`, `expiry = 2025-10-03`, `option_type = "C"`

#### Scenario: Pre-existing equity leg is unchanged by backfill
- **WHEN** the migration runs and a leg's `raw_data` symbol is a plain equity ticker
- **THEN** its `strike`, `expiry`, and `option_type` remain `null`

## MODIFIED Requirements

### Requirement: Execution legs table shows Symbol and Asset Class for COMBO trades, and option contract details for any option leg
The system SHALL display, per execution leg row when the parent trade has `is_combo: true`,
a `Symbol` column and an `Asset Class` column; these two columns SHALL remain hidden for
standard (non-COMBO) trades since a non-COMBO trade has a single, already-known instrument.
Independently of `is_combo`, the system SHALL display `Strike`, `Type` (Call/Put), and
`Expiry` columns whenever the trade has at least one leg with a non-null `option_type` —
this applies equally to a standard single-option trade and to a COMBO trade with option
legs. Option contract columns SHALL render an em dash (`—`) for non-option legs and for
option legs whose contract fields are `null`. When the trade has no option legs at all,
the Strike/Type/Expiry columns SHALL be omitted entirely (not just dashed).

#### Scenario: COMBO trade shows per-leg symbol
- **WHEN** a user opens the trade detail page for a COMBO trade with one EQUITY leg (AAPL EQUITY) and one OPTION leg (AAPL OPTION)
- **THEN** the execution legs table has a Symbol column showing "AAPL" for both rows and an Asset Class column showing "EQUITY" and "OPTION" respectively

#### Scenario: COMBO trade shows per-leg option contract details
- **WHEN** a user opens the trade detail page for a COMBO vertical spread with a QQQ 712 Call leg and a QQQ 722 Call leg
- **THEN** the legs table shows Strike "712.00" / "722.00", Type "Call" / "Call", and the shared Expiry date for the two option rows

#### Scenario: Non-option leg shows dashes for contract columns
- **WHEN** a COMBO trade has an EQUITY leg alongside option legs
- **THEN** the EQUITY row shows "—" in the Strike, Type, and Expiry columns

#### Scenario: Standard trade hides symbol and asset-class columns
- **WHEN** a user opens a non-COMBO trade detail page
- **THEN** no Symbol or Asset Class column is present in the execution legs table

#### Scenario: Standard single-option trade shows Strike/Type/Expiry without Symbol/Asset Class
- **WHEN** a user opens a non-COMBO trade whose single leg has `option_type = "C"`, `strike = 712.00`, `expiry = 2025-10-03`
- **THEN** the execution legs table shows Strike "712.00", Type "Call", and Expiry "Oct 3, 2025" for that row
- **THEN** no Symbol or Asset Class column is present (unchanged, since the trade is not a COMBO)

#### Scenario: Standard equity trade shows no option columns
- **WHEN** a user opens a non-COMBO trade with no option legs
- **THEN** no Symbol, Asset Class, Strike, Type, or Expiry column is present in the execution legs table

---

### Requirement: ExecutionSummaryCard shows a per-instrument breakdown for COMBO trades and a contract label for single-option trades
The system SHALL replace the standard flat grid in `ExecutionSummaryCard` with a per-instrument summary when the trade has `is_combo: true`. Legs SHALL be grouped by `(symbol, asset_class, conid)` so that distinct option contracts (different strikes/expiries) within the same underlying remain visible as separate rows. For each group the card SHALL show: direction (LONG/SHORT), an instrument label, quantity with unit label ("shares" when multiplier=1, "contracts" when multiplier>1), the multiplier value when greater than 1 (displayed as `×50`, `×100`, etc. — taken from `leg.multiplier`, never hardcoded), per-unit price (VWAP of entry legs in the group), and notional value (`quantity × price × multiplier`). For option groups the instrument label SHALL be a **compact** contract label using only the leg's `option_type` and `strike` (e.g. `712 Call`) rather than the raw `conid` — the underlying symbol is omitted (already shown in the trade detail page header) and the expiry date is omitted (already a sortable column in the execution legs table below), to avoid repeating the same text on every row of a multi-leg strategy. Below the instrument rows, a totals row SHALL show combined commission and combined P&L (if available). The standard flat grid (VWAP Entry, VWAP Exit, Total Quantity) SHALL be hidden for COMBO trades.

For standard (non-COMBO) trades with at least one option leg, the card SHALL retain the
flat grid layout but SHALL additionally display a human-readable contract label (e.g.
`QQQ 712 Call · Oct 3 2025`) as a subtitle or annotation, derived from the leg's
`option_type`, `strike`, and `expiry` fields. When those fields are `null` the label SHALL
be omitted. For standard equity trades (no option legs) the card SHALL remain unchanged.

#### Scenario: Vertical spread COMBO shows two contract rows
- **WHEN** a user opens the trade detail page for a COMBO trade containing a QQQ 712C leg and a QQQ 722C leg (different `conid`s)
- **THEN** the ExecutionSummaryCard shows one row labeled for the 712 Call contract and a separate row labeled for the 722 Call contract
- **THEN** a totals row shows combined commission and combined P&L (if broker P&L is available on legs)

#### Scenario: Option instrument label uses compact contract details not conid
- **WHEN** a COMBO trade contains an option leg with `option_type = "C"`, `strike = 712.00`, `expiry = 2025-10-03`
- **THEN** that group's instrument label reads as a compact human-readable contract (e.g. "712 Call") and does not display the raw `conid`, the underlying symbol, or the expiry date as the primary label

#### Scenario: Covered call COMBO shows two instrument rows
- **WHEN** a user opens the trade detail page for a COMBO trade containing 100 AAPL EQUITY LONG legs and 2 AAPL OPTION SHORT legs (multiplier=100)
- **THEN** the ExecutionSummaryCard shows one row for `AAPL EQUITY — LONG — 100 shares — $150.00/share — Notional $15,000`
- **THEN** a second row shows the option contract (e.g. "150 Call") — SHORT — 2 contracts — $5.00/contract — Notional $1,000 (= 2 × $5.00 × 100)
- **THEN** a totals row shows combined commission and combined P&L (if broker P&L is available on legs)

#### Scenario: COMBO card hides VWAP fields
- **WHEN** a user views the ExecutionSummaryCard for a COMBO trade
- **THEN** no `VWAP Entry`, `VWAP Exit`, or `Total Quantity` tiles are visible

#### Scenario: Standard single-option trade shows contract label on summary card
- **WHEN** a user views the ExecutionSummaryCard for a non-COMBO trade whose leg has `option_type = "C"`, `strike = 712.00`, `expiry = 2025-10-03`
- **THEN** the card renders the flat grid layout (VWAP Entry, VWAP Exit, Total Quantity, Commission) with a contract label subtitle (e.g. "QQQ 712 Call · Oct 3 2025")

#### Scenario: Standard equity trade card is unchanged
- **WHEN** a user views the ExecutionSummaryCard for a non-COMBO, non-option trade
- **THEN** the card renders the existing flat grid layout without any contract label
