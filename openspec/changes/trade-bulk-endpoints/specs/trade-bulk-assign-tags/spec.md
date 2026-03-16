## ADDED Requirements

### Requirement: Bulk assign tags to trades
The system SHALL provide a `POST /trades/bulk/assign-tags` endpoint that replaces all tags on multiple trades belonging to the authenticated user in a single atomic operation.

The request body SHALL be:
```json
{ "trade_ids": ["uuid1", "uuid2", ...], "tag_ids": ["tag-uuid1", ...] }
```

The response SHALL be:
```json
{ "affected_count": 2 }
```

Tag assignment SHALL be a full replacement: all existing tags on the selected trades are removed and replaced with the provided `tag_ids`. Providing an empty `tag_ids` array SHALL remove all tags from the selected trades. The system SHALL validate that all provided `tag_ids` belong to the authenticated user and return HTTP 404 if any tag is not found.

#### Scenario: Replaces tags on owned trades
- **WHEN** an authenticated user POSTs valid trade IDs and tag IDs that belong to them
- **THEN** each trade's tags are replaced with exactly the provided tag IDs and `affected_count` reflects the number of trades updated

#### Scenario: Empty tag list clears all tags
- **WHEN** the request has valid trade IDs and an empty `tag_ids` array
- **THEN** all tags are removed from the selected trades and `affected_count` reflects the number of trades updated

#### Scenario: Unknown tag ID returns 404
- **WHEN** the request includes a `tag_id` that does not belong to the authenticated user
- **THEN** the API returns HTTP 404 with an error message

#### Scenario: Exceeding max batch size returns 422
- **WHEN** the request contains more than 500 trade IDs
- **THEN** the API returns HTTP 422

#### Scenario: Unauthenticated request is rejected
- **WHEN** a request is made without a valid JWT
- **THEN** the API returns HTTP 401
