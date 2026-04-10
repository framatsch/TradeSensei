# Code Review Findings — Technical Design

## Architecture Target State

### Layer Separation (AGENTS.md Enforcement)
```
api/v1/       → HTTP only: route handler, HTTPException, status codes
services/     → Business logic: domain exceptions only (app.core.exceptions)
repositories/ → DB queries only: SQLAlchemy, no business logic
models/       → ORM models (never directly to API layer)
schemas/      → Pydantic DTOs (request/response boundary)
core/         → Config, exceptions, constants, security
```

**Rule**: No import of `fastapi.HTTPException` in `services/` or `repositories/`.
**Rule**: No Pydantic schema definitions in `api/v1/` — only in `schemas/`.
**Rule**: No direct session access in route handlers or services (only via `_get_service` DI).

---

## Changes by Priority

### P1 — Critical Architecture Violations

#### CRITICAL-1: `saved_trade_filter_service.py` — HTTPException in Service
**Problem:** `from fastapi import HTTPException` in service layer.
**Fix:**
1. Add to `app/core/exceptions.py`: `SavedTradeFilterNotFoundError`, `SavedTradeFilterPermissionError`, `SavedTradeFilterValidationError`
2. Service: `raise HTTPException(...)` → Domain exceptions
3. `api/v1/saved_trade_filters.py`: Catch domain exceptions, raise HTTPException

#### CRITICAL-2,3,4: DB Queries Directly in Services
- `services/broker_service.py` L90-95, L265-283: `AccountRepository.get_by_id_with_properties()`, `TradeRepository.find_by_broker_order_ids()`, `TradeRepository.bulk_create()`
- `services/import_service.py` L217-225: `CorporateActionRepository.find_by_user_symbol_date_ratio()`
- `services/flex_import_service.py` L397-403: `TradeRepository.find_duplicate(user_id, symbol, opened_at)`

#### CRITICAL-5: `market_data_service.py` — No Repository
**Fix:** New `repositories/ohlc_price_repository.py` with `get_cached_prices()` and `upsert_bars()`. Service delegates to it.

#### CRITICAL-6: `assert` as Runtime Guard in `account_service.py` L151, L194
```python
# Instead of:   assert refreshed is not None
# Fix:
if refreshed is None:
    raise RuntimeError(f"Account {account.id} disappeared after creation/update.")
```

#### CRITICAL-7: `api/v1/executions.py` — Inline Service Construction + Missing ResponseEnvelope
**Problem 1:** Every handler constructs `ExecutionService(session)` inline.
**Problem 2:** Return values not wrapped in `ResponseEnvelope`.
**Problem 3:** `ReassignExecutionRequest` Pydantic schema defined directly in `api/v1/executions.py`.
**Fix:**
1. Add `_get_service` dependency function similar to other routers:
   ```python
   def _get_service(session: Annotated[AsyncSession, Depends(get_session)]) -> ExecutionService:
       return ExecutionService(session)
   ```
2. All handlers: `service: Annotated[ExecutionService, Depends(_get_service)]`
3. Move `ReassignExecutionRequest` and create `ReassignExecutionResponse` in `app/schemas/execution.py`
4. Set `response_model=ResponseEnvelope[T]` on all endpoints
5. Add module docstring

#### CRITICAL-8: `api/v1/cash_transactions.py` — Session Passed to Static Methods
**Problem 1:** Route handler injects session and passes it directly to `CashTransactionService.create(session=session, ...)`.
**Problem 2:** `CashTransactionNotFoundError` not caught → silent 500.
**Fix:**
1. Refactor `CashTransactionService` to instance-based service (see SUGGESTION-2)
2. Add `_get_service` dependency
3. All handlers: `except CashTransactionNotFoundError → HTTP_404_NOT_FOUND`

---

### P2 — Data & Stability Risks

#### WARNING-26: `partial_close_trade` Never Commits
`services/trade_service.py` L371-484: `await self._repo._session.commit()` before `return` is missing.

#### WARNING-19: Fragile OAuth Commit Pattern
`api/v1/auth.py` L452, L621: `request.state.session` pattern → Dead code to remove (commit already happens via `get_session`).

#### WARNING-21,22: Overly Broad `except` in `security.py`
L145, L180, L249: `except (JWTError, ValueError, Exception)` → `except (JWTError, ValueError)`

#### WARNING-27: Access to Private `_session` of Repository
`TradeRepository` needs public `session: AsyncSession` property.
Alternative: `TradeService.__init__` stores session directly as `self._session`.

#### WARNING-28: DB Queries in Route Handler `trades.py`
`bulk_assign_tags` (L153-156) and `bulk_assign_playbook` (L226-231) perform ownership checks directly in handler.
**Fix:** Move ownership validation into `TradeService.bulk_assign_tags()` / `TradeService.bulk_assign_playbook()`.

#### WARNING-29: Global `_http_client` in `market_data.py` — Connection Leak
`_http_client: httpx.AsyncClient | None = None` is never closed.
**Fix:** Register `httpx.AsyncClient` in FastAPI `lifespan` context manager in `main.py` and inject via dependency.

---

### P3 — Code Quality

#### WARNING-1: Misplaced Class Docstring `trade_service.py`
Docstring must appear after `class TradeService:` (before all methods).

#### WARNING-2: Bare `except Exception` Without Logging (`user_service.py`)
Add logger call: `logger.warning("Failed to parse features JSON for user %s", user_id)`

#### WARNING-4,5,6,7: Magic Numbers/Strings → `constants.py`
- `FLEX_POLL_INTERVAL_SECONDS = 2`, `FLEX_POLL_MAX_ATTEMPTS = 10`
- `FLEX_BASE_URL`, `FLEX_API_VERSION`
- `BYTES_PER_MB: int = 1024 * 1024`
- `SECONDS_PER_DAY: int = 86_400`

#### WARNING-9,10,11,12: Services Return ORM Models
- `auth_service.register()` → `UserRead`
- `auth_service.logout()` → Parameter `user_id: uuid.UUID`
- `cash_transaction_service.*` → Pydantic DTOs
- `execution_service.*` → `LogicalExecutionRead` / `TradeRead`

#### WARNING-17: `merge_trades` Route: Manual Service Constructor → DI
```python
service: Annotated[TradeService, Depends(_get_service)]
```

#### WARNING-23,24: Imports Inside Method Bodies
`import json` (`user_service.py`) and `import calendar` (`timeseries_service.py`) to module-level import block.

#### WARNING-25: Deferred Imports Without Explanation Comment
Add comment: `# Deferred import to break circular dependency: execution → trade`

#### WARNING-30: `response_model=None` in `market_data.py`
`get_price_history` declares `response_model=None` with `Any` return type → Define `OHLCResponse` schema.

#### WARNING-31: Magic Status Codes in `market_data.py`
`status_code=502` → `status.HTTP_502_BAD_GATEWAY`

#### WARNING-32: File I/O in Route Handler `screenshots.py`
`upload_screenshot` performs file operations and URL construction directly in handler.
**Fix:** Move to `TradeService.add_screenshot(trade_id, content, suffix)`.

#### WARNING-33: `MAX_FILE_SIZE` in `screenshots.py` → `constants.py`
`SCREENSHOT_MAX_FILE_SIZE_MB: int = 20` to `core/constants.py`.

#### WARNING-34: `type: ignore[import-untyped]` Without Justification in `auth.py`
```python
# type: ignore[import-untyped]  # authlib has no type stubs
```

#### WARNING-35: Query Parameters Without `Query()` Annotation in `broker.py`
Wrap `days`, `from_date`, `overwrite_manually_edited` with `Annotated[..., Query(...)]`.

#### WARNING-36: `Any` Type in `config.py` Without Justification Comment
```python
def parse_cors_origins(cls, value: Any) -> Any:  # Any: pydantic-settings passes raw env value of unknown type
```

#### WARNING-37: `except Exception` in `database.py` Without Justification Comment
```python
except Exception:  # Re-raise after rollback — caller sees the original exception
```

#### WARNING-14,15,16: Missing/Minimal Module Docstrings
`execution.py`, `cash_transaction_service.py`, `saved_trade_filter_service.py` — complete docstrings per project standard.

---

### P4 — Suggestions

- **SUGGESTION-2**: `CashTransactionService` — Refactor from static methods to instance-based service
- **SUGGESTION-6**: Remove dead code `_issue_token_pair` in `auth_service.py`
- **SUGGESTION-7**: Duplicate `NOTE_CONTENT_MAX_LENGTH` → keep only one name, update all imports
- **SUGGESTION-8**: German strings in `tax_service.py` with English explanation comments
- **SUGGESTION-9**: Delete `api/v1/trades_update.py` (its own docstring marks it as obsolete)

---

## Repo Hygiene

Remove from repository (dev artifacts):
```
fix_merge.py
fix_executions_endpoint.py
fix_reports.py
patch_trade_service.py
patch_execution_service.py
backend/patch_create_trade.py
update_merge.py
update_executions_endpoints.py
patch_execution.py
```

---

## Exception-Mapping Convention (API Layer)

Standard pattern for all route handlers:

```python
from app.core.exceptions import ExecutionNotFoundError, ExecutionValidationError, TradeNotFoundError

try:
    result = await service.some_operation(...)
except TradeNotFoundError as exc:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
except ExecutionNotFoundError as exc:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
except (ExecutionValidationError, ValueError) as exc:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
except PermissionError as exc:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
```

Optional: Central mapping via `api/_errors.py` utility function or FastAPI `exception_handler`.

---

## Scope Boundary

This change affects exclusively:
- Structural architecture (layer separation)
- Code quality (types, docstrings, imports, constants)
- Error handling (exception types, HTTP codes)

Explicitly **NOT** changed:
- Business logic (calculations, algorithms, domain rules)
- Database schema or migrations
- API behavior from user perspective (same endpoints, same responses)
- Domain validation rules