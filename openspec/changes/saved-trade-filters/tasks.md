## Implementation Tasks

### Backend
1. Add `saved_trade_filters` model and migration with JSONB definition, scope enum, owner, timestamps, and `needs_review` flag.
2. Add repository methods for list, create, update, delete with ownership and scope checks.
3. Add service layer for validation and permission enforcement; map definition to existing trade filter semantics.
4. Add API endpoints: list, create, update, delete; reject updates/deletes for system scope.
5. Add seed data for system filters with stable identifiers and upsert behavior.
6. Add validation for definition payloads (allow only existing trade query fields).

### Frontend
1. Add Views list in Trades navigation and wire selection to trade query params.
2. Display lock icon for system filters and disable edit/delete actions.
3. Display warning indicator when `needs_review = true`.
4. Add create/edit/delete flow for user-owned filters.

### Tests
1. Unit tests: validation of definitions, ownership enforcement, system read-only behavior.
2. Integration tests: list returns system + user filters, create/update/delete flows.
3. UI tests: lock icon for system filters, warning badge for needs_review.

### Documentation
1. Update OpenAPI docs for saved filter endpoints.
2. Add user-facing description to docs if needed.
