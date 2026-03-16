## ADDED Requirements

### Requirement: Bulk delete trades
The system SHALL provide a `POST /trades/bulk/delete` endpoint that deletes multiple trades belonging to the authenticated user in a single atomic operation.

The request body SHALL be:
```json
{ "trade_ids": ["uuid1", "uuid2", ...] }
```

The response SHALL be:
```json
{ "affected_count": 2 }
```

The system SHALL silently skip any `trade_id` values that do not belong to the authenticated user. The system SHALL reject requests where `trade_ids` contains more than 500 entries with HTTP 422. The system SHALL return HTTP 200 with `affected_count: 0` for empty `trade_ids`.

#### Scenario: Successfully deletes owned trades
- **WHEN** an authenticated user POSTs valid trade IDs that belong to them
- **THEN** those trades are deleted and the response contains the correct `affected_count`

#### Scenario: Skips foreign trade IDs silently
- **WHEN** the request includes IDs belonging to another user
- **THEN** those IDs are skipped, own trades are deleted, and `affected_count` reflects only the user's deleted trades

#### Scenario: Empty list returns 200 with zero count
- **WHEN** the request contains an empty `trade_ids` array
- **THEN** the response is HTTP 200 with `affected_count: 0`

#### Scenario: Exceeding max batch size returns 422
- **WHEN** the request contains more than 500 trade IDs
- **THEN** the API returns HTTP 422

#### Scenario: Unauthenticated request is rejected
- **WHEN** a request is made without a valid JWT
- **THEN** the API returns HTTP 401
