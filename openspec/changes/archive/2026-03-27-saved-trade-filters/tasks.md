## Implementation Tasks

### Backend
- [x] Add `saved_trade_filters` model and migration with JSONB definition, scope enum, owner, timestamps, and `needs_review` flag.
- [x] Add repository methods for list, create, update, delete with ownership and scope checks.
- [x] Add service layer for validation and permission enforcement; map definition to existing trade filter semantics.
- [x] Add API endpoints: list, create, update, delete; reject updates/deletes for system scope.
- [x] Add seed data for system filters with stable identifiers and upsert behavior.
- [x] Add validation for definition payloads (allow only existing trade query fields).

### Frontend
- [x] Add Views list in Trades navigation and wire selection to trade query params.
- [x] Display lock icon for system filters and disable edit/delete actions.
- [x] Display warning indicator when `needs_review = true`.
- [x] Add create/edit/delete flow for user-owned filters.

### Tests
- [x] Unit tests: validation of definitions, ownership enforcement, system read-only behavior.
- [x] Integration tests: list returns system + user filters, create/update/delete flows.
- [x] UI tests: lock icon for system filters, warning badge for needs_review.

### Documentation
- [x] Update OpenAPI docs for saved filter endpoints.
- [x] Add user-facing description to docs if needed.
