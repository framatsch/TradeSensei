## ADDED Requirements

### Requirement: Magic integer status codes must use fastapi.status constants
Route handlers MUST use `fastapi.status.HTTP_*` named constants instead of bare integer
literals for HTTP status codes (both in `@router` decorators and in `raise HTTPException`).

#### Scenario: accounts.py delete uses HTTP_404_NOT_FOUND
- **WHEN** `delete_account` raises a not-found error
- **THEN** the code SHALL read `status.HTTP_404_NOT_FOUND`, not `404`

#### Scenario: market_data.py uses HTTP_502_BAD_GATEWAY
- **WHEN** the upstream data provider returns an error
- **THEN** the code SHALL use `status.HTTP_502_BAD_GATEWAY`, not `502`

---

### Requirement: Query parameters must be declared with Query() annotation
FastAPI query parameters that carry validation constraints or OpenAPI descriptions MUST
be declared with `Annotated[T, Query(...)]` so that constraints and descriptions appear
in the generated OpenAPI schema.

#### Scenario: broker.py sync parameters are documented
- **WHEN** the OpenAPI schema is generated for `POST /api/v1/broker/sync`
- **THEN** `days`, `from_date`, and `overwrite_manually_edited` SHALL have descriptions in the schema

---

### Requirement: All response types must have explicit response_model
Every `@router.*` decorator MUST specify `response_model`. Using `response_model=None`
or omitting it is only permissible when the response is a raw streaming or binary response,
and MUST be documented with a comment.

#### Scenario: market_data.py get_price_history has response_model
- **WHEN** the OpenAPI schema is generated for the price history endpoint
- **THEN** the response schema SHALL be defined (not `{}` or absent)

#### Scenario: executions.py reassign_execution has response_model
- **WHEN** the OpenAPI schema is generated for `POST /executions/{id}/reassign`
- **THEN** the response schema SHALL be `ResponseEnvelope[ReassignExecutionResponse]`

---

### Requirement: Dead OAuth commit code must be removed
The silent-no-op `await request.state.session.commit() if hasattr(request.state, "session") else None`
pattern in `auth.py` MUST be removed because the commit is already performed by the
`get_session` dependency; this code never executes the commit and misleads future readers.

#### Scenario: auth.py lines 452 and 621 are clean
- **WHEN** `auth.py` is reviewed
- **THEN** no `request.state.session` references SHALL appear in OAuth callback handlers

---

### Requirement: api/v1/ files must have module-level docstrings
Every `api/v1/*.py` router file MUST have a module-level docstring following the project
standard (one-sentence description of the resource handled).

#### Scenario: executions.py has module docstring
- **WHEN** `pydoc` introspects `app.api.v1.executions`
- **THEN** a non-empty module docstring SHALL be returned

---

### Requirement: type: ignore comments must include a justification
Every `# type: ignore[...]` in `api/v1/` files MUST have an inline justification comment.

#### Scenario: auth.py import-untyped is justified
- **WHEN** mypy processes `auth.py`
- **THEN** the `# type: ignore[import-untyped]` on the authlib import SHALL have a comment:
  `# authlib has no type stubs`
