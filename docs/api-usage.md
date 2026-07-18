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
