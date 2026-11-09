## ADDED Requirements

### Requirement: Trade Sensei Execution Format v1 — JSON envelope
The system SHALL accept a JSON document with the root fields `format` (required, constant `"tradesensei.executions"`), `version` (required, `"1.x"`; any other major version SHALL be rejected), `source` (optional string ≤ 100 characters, informational only, never used for identity), `executions` (required, non-empty array of execution objects) and `corporate_actions` (optional array of split objects). Unknown root fields SHALL be rejected.

#### Scenario: Valid minimal document
- **WHEN** a document with `format`, `version: "1.0"` and one valid execution is validated
- **THEN** validation SHALL succeed

#### Scenario: Unsupported major version
- **WHEN** a document declares `version: "2.0"`
- **THEN** validation SHALL fail with an error on field `version`

#### Scenario: Wrong format marker
- **WHEN** `format` is missing or not `"tradesensei.executions"`
- **THEN** validation SHALL fail before any execution is inspected

### Requirement: Execution record fields
Each execution SHALL be validated against these fields; unknown fields SHALL be rejected:

| Field | Type | Required | Rule |
|---|---|---|---|
| `external_id` | string 1–100 | no | Broker's unique per-fill ID; trimmed |
| `executed_at` | RFC 3339 timestamp | yes | MUST include a UTC offset or `Z`; stored as UTC; MUST NOT be more than 24 h in the future |
| `symbol` | string | yes | Upper-cased; for options the **underlying** ticker |
| `asset_class` | enum | yes | `EQUITY`, `OPTION`, `FUTURE`, `FOREX`, `CRYPTO` |
| `side` | enum | yes | `BUY`, `SELL` |
| `position_effect` | enum | no | `OPEN`, `CLOSE`, `CLOSE_OPEN` (position flip); absent = unknown |
| `quantity` | decimal | yes | > 0, absolute |
| `price` | decimal | yes | ≥ 0, per unit |
| `commission` | decimal | no | ≥ 0, absolute total fees; default 0 |
| `currency` | string | yes | ISO 4217, 3 upper-case letters |
| `multiplier` | integer | conditional | ≥ 1; required for `OPTION` and `FUTURE`, default 1 otherwise |
| `order_id` | string 1–100 | no | Groups fills/legs of one order (combo detection) |
| `contract_id` | string 1–50 | no | Broker contract identifier |
| `option.strike` | decimal | if OPTION | > 0 |
| `option.expiry` | date `YYYY-MM-DD` | if OPTION | |
| `option.right` | enum | if OPTION | `C`, `P` |
| `realized_pnl` | decimal | no | Broker-reported realized P&L, informational |

The `option` object SHALL be required when `asset_class` is `OPTION` and SHALL be rejected otherwise. Decimal values SHALL be accepted as JSON strings or JSON numbers and SHALL be parsed losslessly as `Decimal` (never via binary float).

#### Scenario: Naive timestamp rejected
- **WHEN** an execution has `executed_at: "2026-10-02T14:31:07"` without offset
- **THEN** validation SHALL fail on that row's `executed_at`

#### Scenario: Option without option object
- **WHEN** an execution has `asset_class: "OPTION"` and no `option` object
- **THEN** validation SHALL fail on that row's `option`

#### Scenario: Typo in field name
- **WHEN** an execution contains the unknown field `comission`
- **THEN** validation SHALL fail on that row naming the unknown field

#### Scenario: Lossless decimals
- **WHEN** an execution has `price: 0.1` as a JSON number
- **THEN** the stored price SHALL be exactly `0.1`

### Requirement: CSV variant
The system SHALL accept a CSV file (UTF-8, optional BOM, comma delimiter, RFC 4180 quoting, header row required) whose columns are the execution fields with the option object flattened to `option_strike`, `option_expiry`, `option_right`. Decimal separator SHALL be `.` with no thousands separators. Empty cells SHALL mean "absent". Unknown columns SHALL be rejected. The CSV variant SHALL carry executions only; splits require the JSON variant.

#### Scenario: Valid CSV
- **WHEN** a CSV with header `executed_at,symbol,asset_class,side,quantity,price,currency` and valid rows is validated
- **THEN** validation SHALL succeed and produce the same canonical executions as the equivalent JSON

#### Scenario: Locale-formatted number
- **WHEN** a CSV cell contains `1.234,50`
- **THEN** validation SHALL fail on that cell

### Requirement: File-level consistency rules
Validation SHALL be all-or-nothing. A file SHALL be rejected if: any row is invalid; an `external_id` occurs more than once; some executions have `external_id` and others do not; the file exceeds the configured import size limit. Errors SHALL be returned as a list of `{row, field, code, message}` (row = 1-based data row for CSV, 0-based array index for JSON), capped at 200 entries, and SHALL NOT echo prices, quantities or P&L values.

#### Scenario: Duplicate external_id
- **WHEN** two executions share `external_id: "TT-1"`
- **THEN** the whole file SHALL be rejected with error code `duplicate_external_id` on both rows and nothing SHALL be written

#### Scenario: Mixed ID presence
- **WHEN** some executions carry `external_id` and others do not
- **THEN** the file SHALL be rejected with error code `mixed_id_strategy`

### Requirement: Split records (JSON only)
Each entry in `corporate_actions` SHALL have `type` (`SPLIT`), `symbol`, `date` (`YYYY-MM-DD`), `ratio` (decimal > 0, shares after / shares before) and optional `old_contract_id`, `new_contract_id`.

#### Scenario: Reverse split
- **WHEN** a split with `ratio: "0.1"` is validated
- **THEN** validation SHALL succeed

### Requirement: Format publication
The format SHALL be published as: an OpenAPI component (generated from the Pydantic models), a JSON Schema at `GET /api/v1/imports/formats/generic`, a CSV template with header row and two example rows at `GET /api/v1/imports/formats/generic/template.csv`, the guide `docs/import-generic-format.md`, and a Help page section. All published artefacts SHALL be derived from or tested against the same Pydantic models.

#### Scenario: Schema endpoint
- **WHEN** an authenticated user requests `GET /api/v1/imports/formats/generic`
- **THEN** the response SHALL be the JSON Schema of the v1 document and SHALL validate the example in the guide

#### Scenario: Docs cannot drift
- **WHEN** the test suite runs
- **THEN** the JSON example and CSV template from the docs SHALL be validated against the models and SHALL pass
