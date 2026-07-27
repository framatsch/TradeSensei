# API Usage Notes

## Clear All Trades (Account-Scoped)

Use this endpoint to reset an account's imported and manually edited trade data
without deleting the account itself.

- Method: `DELETE`
- Path: `/api/v1/portfolios/{portfolio_id}/accounts/{account_id}/trades`
- Query param: `acknowledged=true` (required)

Behavior:

- Deletes all `trades`, `logical_executions`, and `broker_raw_transactions` for
  the account.
- Preserves the account row and account settings.
- Returns deletion counts in `ResponseEnvelope[ClearTradesResult]`.
- Returns `400` when `acknowledged` is missing/false.
- Returns `404` when the account is not owned by the authenticated user.

Example:

```bash
curl -X DELETE \
  "http://localhost:8000/api/v1/portfolios/<portfolio_id>/accounts/<account_id>/trades?acknowledged=true" \
  -H "Authorization: Bearer <access_token>"
```

## Import UI Date Range (IBKR + Schwab)

The frontend sync UI now uses one shared date-range control for both IBKR and
Schwab.

- IBKR sync requests send `from_date=YYYYMMDD`.
- Schwab sync requests send `days=<N>`.

The control enforces broker-specific max window limits from a capability
descriptor and removes broker-specific component branching.

## Execution Leg Shape (Options)

For option trades (where `asset_class` is `"OPTION"` or when part of a COMBO trade), `LogicalExecution` objects in API responses (e.g. `GET /api/v1/trades/{id}`) will include strongly-typed option instrument fields:

- `strike` (string/decimal): Option strike price (e.g., `"712.00000000"`).
- `expiry` (string): Option expiration date in `YYYY-MM-DD` format.
- `option_type` (string): `"C"` for Call, `"P"` for Put.

For non-option legs, these fields will be `null`. The raw OCC string or broker-specific symbol remains accessible in the `symbol` field.


## Link Manual Execution to Broker Transaction

Use this endpoint to link an unlinked manual execution leg (`origin="manual"`) to a raw broker transaction (`BrokerRawTransaction`).

- Method: `POST`
- Path: `/api/v1/portfolios/{portfolio_id}/executions/{execution_id}/link-broker-transaction`
- Auth required: `Bearer <token>`

Request body (`LinkBrokerTransactionRequest`):

```json
{
  "raw_transaction_id": "user:ibkr:3820422546"
}
```

Behavior:

- Atomically links the manual execution leg to the specified raw broker transaction (`source_id = raw_transaction_id`) and sets `suppressed = true` on the broker raw transaction.
- Triggers background trade re-aggregation for affected trades, auto-clearing any duplicate conflict flags.
- Deleting a linked manual execution automatically un-suppresses (`suppressed = false`) the associated raw transaction in the same transaction.

Example request:

```bash
curl -X POST \
  "http://localhost:8000/api/v1/portfolios/3fa85f64-5717-4562-b3fc-2c963f66afa6/executions/3fa85f64-5717-4562-b3fc-2c963f66afa7/link-broker-transaction" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{ "raw_transaction_id": "user:ibkr:3820422546" }'
```

Example response (`ResponseEnvelope[LinkBrokerTransactionResponse]`):

```json
{
  "data": {
    "execution": {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa7",
      "trade_id": "3fa85f64-5717-4562-b3fc-2c963f66afa8",
      "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "account_id": "3fa85f64-5717-4562-b3fc-2c963f66afa9",
      "symbol": "AAPL",
      "direction": "LONG",
      "quantity": "100.00000000",
      "price": "175.50000000",
      "commission": "1.00000000",
      "executed_at": "2026-04-15T14:30:00Z",
      "asset_class": "EQUITY",
      "multiplier": 1,
      "origin": "manual",
      "deleted": false,
      "user_modified": false,
      "source_id": "user:ibkr:3820422546",
      "parent_id": null,
      "created_at": "2026-04-15T14:30:00Z",
      "updated_at": "2026-04-15T14:35:00Z"
    },
    "message": "Execution linked to broker transaction."
  },
  "error": null
}
```

Error responses:

- `404 Not Found`: Execution or broker raw transaction does not exist or is not owned by the user.
- `409 Conflict`: Execution `origin` is not `"manual"`, or the raw broker transaction is already linked to another execution.
- `422 Unprocessable Content`: Invalid request body (e.g. missing `raw_transaction_id`).



## Trade Conflict Detection (has_conflict)

The `TradeRead` schema returned by trade endpoints (e.g., `GET /api/v1/portfolios/{portfolio_id}/trades/{id}`) includes a derived boolean field:

- `has_conflict` (boolean): Set to `true` when a trade contains an unlinked manual execution leg (`origin="manual"`, `source_id=null`) that duplicates an imported leg (`origin="imported"`) matching on symbol, execution time (to the second), direction, quantity, and price.

Behavior:

- `has_conflict` is a read-only derived flag calculated during trade aggregation. It cannot be set directly via `PATCH /trades/{id}`.
- Auto-clears to `false` when the duplicate leg is deleted or when the manual leg is linked to a raw broker transaction using `POST /executions/{id}/link-broker-transaction`.

