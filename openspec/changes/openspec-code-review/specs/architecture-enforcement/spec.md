## ADDED Requirements

### Requirement: Service layer must not import HTTP concepts
No file under `backend/app/services/` SHALL import `fastapi.HTTPException` or any other
HTTP-specific concept. Services MUST raise domain exceptions defined in `app/core/exceptions.py`.
Route handlers in `api/v1/` are the only layer permitted to raise `HTTPException`.

#### Scenario: SavedTradeFilterService raises domain exceptions
- **WHEN** a saved trade filter is not found
- **THEN** the service SHALL raise `SavedTradeFilterNotFoundError` (not `HTTPException`)

#### Scenario: Route handler maps domain exceptions to HTTP responses
- **WHEN** a route handler catches `SavedTradeFilterNotFoundError`
- **THEN** it SHALL raise `HTTPException(status_code=status.HTTP_404_NOT_FOUND, ...)`

#### Scenario: Service layer is free of HTTP imports
- **WHEN** ruff or mypy scans `backend/app/services/`
- **THEN** no import of `fastapi` SHALL be present in any service file

---

### Requirement: DB queries must be delegated to repositories
Services MUST NOT execute raw SQLAlchemy queries directly. All database access MUST go
through repository classes in `backend/app/repositories/`.

#### Scenario: BrokerService delegates account lookup
- **WHEN** `BrokerService.sync_account` needs to load an account
- **THEN** it SHALL call `AccountRepository` methods, not `session.execute(select(Account)...)`

#### Scenario: ImportService delegates corporate action lookup
- **WHEN** `ImportService` checks for duplicate corporate actions
- **THEN** it SHALL call `CorporateActionRepository.find_by_user_symbol_date_ratio()`

#### Scenario: FlexImportService delegates trade duplicate check
- **WHEN** `FlexImportService` checks for duplicate trades
- **THEN** it SHALL call `TradeRepository.find_duplicate()`

#### Scenario: MarketDataService delegates OHLC persistence
- **WHEN** `MarketDataService` needs to read or write OHLC price bars
- **THEN** it SHALL call `OhlcPriceRepository` methods

---

### Requirement: OhlcPriceRepository must exist
A `repositories/ohlc_price_repository.py` SHALL be created with at minimum:
- `get_cached_prices(symbol, start, end)` — returns cached OHLC bars
- `upsert_bars(bars)` — inserts or updates OHLC bars

#### Scenario: Repository created and used by MarketDataService
- **WHEN** `MarketDataService` is instantiated with a session
- **THEN** it SHALL delegate all OHLC DB operations to `OhlcPriceRepository`

---

### Requirement: assert statements must not be used as runtime guards
Services and repositories MUST NOT use Python `assert` statements as runtime guards
for invariants that can occur in production (e.g. post-DB-query checks). These are
silently disabled in optimized mode (`python -O`). Use explicit `if ... raise` instead.

#### Scenario: AccountService uses explicit guard
- **WHEN** a freshly created account cannot be reloaded from DB
- **THEN** the service SHALL raise `RuntimeError(f"Account {account.id} disappeared after creation/update.")`
- **THEN** it SHALL NOT use `assert refreshed is not None`

---

### Requirement: API route handlers must use dependency injection for services
Every router in `api/v1/` MUST use a `_get_service` FastAPI dependency function to obtain
its service instance. Services MUST NOT be constructed inline inside handler functions.

#### Scenario: ExecutionService injected via Depends
- **WHEN** an execution route handler is called
- **THEN** the `ExecutionService` instance SHALL come from `Depends(_get_service)`, not from `ExecutionService(session)` inline

#### Scenario: merge_trades uses DI
- **WHEN** `merge_trades` handler in `trades.py` is called
- **THEN** `TradeService` SHALL come from `Depends(_get_service)`, not from a manual constructor call

---

### Requirement: All endpoints must use ResponseEnvelope
Every `api/v1/` route handler MUST wrap its return value in the project's `ResponseEnvelope`
and declare `response_model=ResponseEnvelope[T]`.

#### Scenario: Execution endpoints return ResponseEnvelope
- **WHEN** any execution endpoint returns data
- **THEN** the response SHALL be wrapped in `ResponseEnvelope[T]`
- **THEN** the `@router.*` decorator SHALL have `response_model=ResponseEnvelope[T]`

---

### Requirement: Pydantic schemas must not be defined in api/v1/ files
All Pydantic `BaseModel` subclasses used as request or response bodies MUST be defined in
`backend/app/schemas/`. No schema class SHALL be defined inline in a `api/v1/` file.

#### Scenario: ReassignExecutionRequest moved to schemas
- **WHEN** `executions.py` is reviewed
- **THEN** no `BaseModel` subclass SHALL be defined in that file
- **THEN** `ReassignExecutionRequest` and `ReassignExecutionResponse` SHALL exist in `app/schemas/execution.py`

---

### Requirement: Session must not be passed directly to service methods
Route handlers MUST NOT inject an `AsyncSession` and pass it as a parameter to service
static methods. The session lifecycle is managed exclusively by the `get_session` dependency.

#### Scenario: CashTransactionService refactored to instance-based
- **WHEN** a cash transaction route handler handles a request
- **THEN** it SHALL obtain a `CashTransactionService` instance via `Depends(_get_service)`
- **THEN** the handler SHALL NOT directly call `CashTransactionService.create(session=session, ...)`

---

### Requirement: DB queries in route handlers must be moved to services
Route handlers MUST NOT execute SQLAlchemy queries. Any ownership or existence check
currently in a handler MUST be moved to the appropriate service method.

#### Scenario: bulk_assign_tags ownership check in service
- **WHEN** `bulk_assign_tags` handler is called
- **THEN** the ownership validation SQL MUST execute inside `TradeService.bulk_assign_tags()`
- **THEN** the route handler SHALL only call the service method and handle exceptions

---

### Requirement: TradeService must not access private repository attributes
`TradeService` MUST NOT access `self._repo._session` (a private attribute of the repository).
Session access within the service MUST go through a public interface.

#### Scenario: TradeService uses its own session reference
- **WHEN** `TradeService` needs to call `session.commit()`, `session.flush()`, or `session.refresh()`
- **THEN** it SHALL use `self._session` stored during `__init__`, not `self._repo._session`

---

### Requirement: Explicit commit calls inside service methods must be removed
Services MUST NOT call `session.commit()` directly. Transaction management (commit/rollback)
is exclusively the responsibility of the `get_session` dependency generator.

#### Scenario: TradeService.create_trade does not commit
- **WHEN** `TradeService.create_trade` completes successfully
- **THEN** it SHALL NOT call `await session.commit()`
- **THEN** the `get_session` dependency SHALL handle the commit on clean request exit

#### Scenario: partial_close_trade does not lose data
- **WHEN** `TradeService.partial_close_trade` completes
- **THEN** all changes SHALL be persisted (the `get_session` dependency commits on clean exit)

---

### Requirement: NotFound exceptions must be caught in route handlers
Route handlers MUST catch domain `NotFoundError` exceptions raised by services and
translate them to `HTTP_404_NOT_FOUND` responses, not let them propagate as 500s.

#### Scenario: CashTransaction 404 instead of 500
- **WHEN** `get_cash_transaction` is called with a non-existent ID
- **THEN** the handler SHALL return `HTTP_404_NOT_FOUND`
- **THEN** no unhandled exception SHALL reach the ASGI server

---

### Requirement: httpx AsyncClient must be managed in lifespan
Module-level mutable `httpx.AsyncClient` singletons MUST be registered in the FastAPI
`lifespan` context manager in `main.py` so that connections are properly closed on shutdown.

#### Scenario: Client closed on application shutdown
- **WHEN** the FastAPI application shuts down
- **THEN** the `httpx.AsyncClient` used by `market_data.py` SHALL be closed
- **THEN** no `ResourceWarning: unclosed client session` SHALL appear in logs
