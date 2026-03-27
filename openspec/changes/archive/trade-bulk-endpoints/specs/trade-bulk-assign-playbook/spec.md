## ADDED Requirements

### Requirement: Bulk assign playbook to trades
The system SHALL provide a `POST /trades/bulk/assign-playbook` endpoint that sets the playbook on multiple trades belonging to the authenticated user in a single atomic operation.

The request body SHALL be:
```json
{ "trade_ids": ["uuid1", "uuid2", ...], "playbook_id": "playbook-uuid" }
```

Passing `null` for `playbook_id` SHALL remove the playbook assignment from all selected trades. The system SHALL validate that the `playbook_id` belongs to the authenticated user and return HTTP 404 if not found (except when `null`).

The response SHALL be:
```json
{ "affected_count": 2 }
```

#### Scenario: Assigns playbook to owned trades
- **WHEN** an authenticated user POSTs valid trade IDs and a playbook ID that belongs to them
- **THEN** each trade's `playbook_id` is set and `affected_count` reflects the number of updated trades

#### Scenario: Null playbook clears assignment
- **WHEN** the request has valid trade IDs and `"playbook_id": null`
- **THEN** the `playbook_id` field is set to null on all selected trades

#### Scenario: Unknown playbook ID returns 404
- **WHEN** the request includes a `playbook_id` that does not belong to the authenticated user
- **THEN** the API returns HTTP 404

#### Scenario: Exceeding max batch size returns 422
- **WHEN** the request contains more than 500 trade IDs
- **THEN** the API returns HTTP 422

#### Scenario: Unauthenticated request is rejected
- **WHEN** a request is made without a valid JWT
- **THEN** the API returns HTTP 401
