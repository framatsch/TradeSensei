## 1. Domain Exceptions & Core Infrastructure

- [x] 1.1 Add `SavedTradeFilterNotFoundError`, `SavedTradeFilterPermissionError`, `SavedTradeFilterValidationError` to `app/core/exceptions.py` *(`ExecutionNotFoundError`, `ExecutionValidationError`, `TradeValidationError` already added)*
- [x] 1.2 Add constants to `app/core/constants.py`: `BYTES_PER_MB`, `FLEX_POLL_INTERVAL_SECONDS`, `FLEX_POLL_MAX_ATTEMPTS`, `FLEX_BASE_URL`, `FLEX_API_VERSION`, `SCREENSHOT_MAX_FILE_SIZE_MB`, `SECONDS_PER_DAY`
- [x] 1.3 Consolidate duplicate `NOTE_CONTENT_MAX_LENGTH` constant — keep one name, update all imports
- [x] 1.4 Add public `session` property to `TradeRepository` (or store session in `TradeService.__init__` as `self._session`)

## 2. New Repository: OhlcPriceRepository

- [x] 2.1 Create `backend/app/repositories/ohlc_price_repository.py` with `get_cached_prices(symbol, start, end)` and `upsert_bars(bars)` methods
- [x] 2.2 Add full type annotations and Google-style docstring to `OhlcPriceRepository`

## 3. P1 — Critical Architecture Fixes (Services)

- [x] ~~`services/execution.py`: Replace all `HTTPException` with `ExecutionNotFoundError`, `TradeNotFoundError`, `ExecutionValidationError` — **done**~~
- [x] 3.1 `services/saved_trade_filter_service.py`: Replace all `raise HTTPException(...)` with domain exceptions; remove `from fastapi import HTTPException` import; add module docstring
- [x] 3.2 `api/v1/saved_trade_filters.py`: Catch `SavedTradeFilterNotFoundError` → `HTTP_404_NOT_FOUND`, `SavedTradeFilterPermissionError` → `HTTP_403_FORBIDDEN`, `SavedTradeFilterValidationError` → `HTTP_422_UNPROCESSABLE_ENTITY`
- [x] 3.3 `services/broker_service.py` L90-95: Replace inline `session.execute(select(Account)...)` with `AccountRepository` call; add method `get_by_id_with_properties` to `AccountRepository` if missing
- [x] 3.4 `services/broker_service.py` L265-283: Replace inline trade queries with `TradeRepository.find_by_broker_order_ids()` and `TradeRepository.bulk_create()` (add methods if missing)
- [x] 3.5 `services/import_service.py` L217-225: Replace inline corporate action query with `CorporateActionRepository.find_by_user_symbol_date_ratio()` (add method if missing)
- [x] 3.6 `services/flex_import_service.py` L397-403: Replace inline trade query with `TradeRepository.find_duplicate()` (add method if missing); replace magic numbers/strings with constants from 1.2
- [x] 3.7 `services/market_data_service.py`: Replace all direct DB access with `OhlcPriceRepository` calls; fix missing `-> None` type annotation on `__init__`
- [x] 3.8 `services/account_service.py` L151, L194: Replace `assert refreshed is not None` with explicit `if refreshed is None: raise RuntimeError(...)`

## 4. P1 — Critical Architecture Fixes (API Layer)

- [x] 4.1 `api/v1/executions.py`: Add `_get_service` dependency function; refactor all handlers to use `Depends(_get_service)` instead of inline `ExecutionService(session)` construction
- [x] 4.2 `api/v1/executions.py`: Wrap all return values in `ResponseEnvelope[T]`; set `response_model=ResponseEnvelope[T]` on all `@router.*` decorators
- [x] 4.3 Move `ReassignExecutionRequest` and create `ReassignExecutionResponse` in `app/schemas/execution.py`; set `response_model=ResponseEnvelope[ReassignExecutionResponse]` on `reassign_execution`
- [x] 4.4 Add module-level docstring to `api/v1/executions.py`
- [x] 4.5 `services/cash_transaction_service.py`: Refactor from static methods to instance-based service with `__init__(self, session: AsyncSession)`
- [x] 4.6 `api/v1/cash_transactions.py`: Add `_get_service` dependency function; refactor all handlers to use `Depends(_get_service)`
- [x] 4.7 `api/v1/cash_transactions.py`: Add `except CashTransactionNotFoundError` → `HTTP_404_NOT_FOUND` to `get_cash_transaction`, `update_cash_transaction`, and `delete_cash_transaction`

## 5. P2 — Stability & Data Risks

- [x] 5.1 `services/trade_service.py`: Fix misplaced class docstring — move to immediately after `class TradeService:`
- [x] 5.2 `services/trade_service.py`: Remove explicit `await session.commit()` calls from `create_trade` (L97) and `merge_trades` (L363); rely on `get_session` dependency for transaction management *(`merge_trades` HTTPException already replaced with `TradeNotFoundError`/`ValueError` — commit() still present at L363)*
- [x] 5.3 `services/trade_service.py`: Replace all `self._repo._session` accesses with `self._session` (after fix 1.4) *(still present at L42, L77, L97, L336, L344, L363, L423, L471, L480, L481)*
- [x] 5.4 `api/v1/trades.py` L153-156, L226-231: Move ownership-check SQL from `bulk_assign_tags` and `bulk_assign_playbook` handlers into `TradeService.bulk_assign_tags()` / `TradeService.bulk_assign_playbook()`
- [x] 5.5 `api/v1/trades.py` L593-600 (`merge_trades`): Replace inline `TradeService(session)` with `service: Annotated[TradeService, Depends(_get_service)]`
- [x] 5.6 `api/v1/auth.py` L452, L621: Remove dead `request.state.session.commit()` lines
- [x] 5.7 `core/security.py` L145, L180, L249: Narrow `except (JWTError, ValueError, Exception)` → `except (JWTError, ValueError)`
- [x] 5.8 `api/v1/market_data.py` L36: Register `httpx.AsyncClient` in `main.py` `lifespan` context manager; inject via dependency instead of module-level singleton

## 6. P3 — Code Quality

- [x] 6.1 `services/user_service.py` L151, L187: Add `logger.warning(...)` to both bare `except Exception` blocks
- [x] 6.2 `services/user_service.py` L142, L175: Move `import json` to module-level import block
- [x] 6.3 `services/user_service.py` L154: Add justification comment to `# type: ignore`
- [x] 6.4 `services/timeseries_service.py` L178: Move `import calendar` to module-level import block
- [x] 6.5 `services/trade_service.py` L36, L74, L334, L367, L469: Add comment to each deferred import: `# Deferred import to break circular dependency: execution → trade`
- [x] 6.6 `services/execution.py` L1: Add module-level docstring
- [x] 6.7 `services/cash_transaction_service.py` L1: Add complete module-level docstring (after refactor from 4.5)
- [x] 6.8 `api/v1/market_data.py` L73-84: Define `OHLCResponse` schema in `app/schemas/market_data.py` (or existing schema file) and set as `response_model`
- [x] 6.9 `api/v1/market_data.py` L146, L157: Replace integer literals `502` with `status.HTTP_502_BAD_GATEWAY`
- [x] 6.10 `api/v1/accounts.py` L266: Replace bare `404` with `status.HTTP_404_NOT_FOUND`
- [x] 6.11 `api/v1/auth.py` L10: Add justification comment to `# type: ignore[import-untyped]`: `# authlib has no type stubs`
- [x] 6.12 `api/v1/broker.py` L65-67: Wrap `days`, `from_date`, `overwrite_manually_edited` with `Annotated[..., Query(description="...")]`
- [x] 6.13 `api/v1/screenshots.py` L86-109: Move file-save logic and URL construction into `TradeService.add_screenshot(trade_id, content, suffix)`; use `SCREENSHOT_MAX_FILE_SIZE_MB` from constants
- [x] 6.14 `core/security.py` L190-191: Add comment above `_used_ott_jti` documenting in-memory limitation and multi-process production constraint
- [x] 6.15 `core/database.py` L60: Add inline comment on `except Exception` re-raise block
- [x] 6.16 `core/config.py` L137: Add justification comment to `Any` type in `parse_cors_origins`
- [x] 6.17 `services/flex_import_service.py` L38-39, L36-37: Replace magic numbers and strings with constants from 1.2
- [x] 6.18 `schemas/execution.py` `LogicalExecutionUpdate`: Add `@field_validator("executed_at", mode="after")` to reject naive datetimes — mirrors the `require_timezone` validator already present in `LogicalExecutionBase`
- [x] 6.19 `services/execution.py` `_re_aggregate_trade`: Move `from decimal import Decimal` out of the method body to the module-level import block; add comment to the deferred `from app.models.trade import Direction` import: `# Deferred import to break circular dependency: trade → execution`

## 7. Repo Hygiene

- [x] 7.1 Delete all patch/fix scripts (currently untracked in repo root: `patch_execution.py`, `patch_trade.py`; check also: `fix_merge.py`, `fix_executions_endpoint.py`, `fix_reports.py`, `patch_trade_service.py`, `patch_execution_service.py`, `backend/patch_create_trade.py`, `update_merge.py`, `update_executions_endpoints.py`)
- [x] 7.2 Delete `api/v1/trades_update.py` and remove its import from `router.py` if present
- [x] 7.3 `services/auth_service.py` L267-278: Delete `_issue_token_pair` dead code method
- [x] 7.4 `services/tax_service.py` L25-26: Add English inline comments explaining German string literals

## 8. Agent Guardrails

- [x] ~~`.opencode/agents/backend-engineer.md`: "Anti-Patterns — Never Do These" section added with all 4 groups (Service Layer, API Layer, Core Layer, Repo & Exception Hygiene) — **done**~~

## 9. Verification

- [x] 9.1 Run `grep -r "from fastapi import" backend/app/services/` — result MUST be empty
- [x] 9.2 Run `grep -r "session.execute" backend/app/services/` — result MUST be empty (all queries via repositories)
- [x] 9.3 Run `grep -r "assert " backend/app/services/` — verify no assert used as runtime guard
- [x] 9.4 Run lint check (`ruff check backend/` and `mypy --strict backend/`) — must pass with 0 errors
- [x] 9.5 Run unit tests (`pytest backend/tests/`) — must pass with no regressions
