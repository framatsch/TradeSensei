# OpenSpec: Code Review Findings & Enforcement (openspec-code-review)

## What

This change documents all architecture violations and code quality issues found in the
complete code review of `backend/app/` and `backend/app/core/`, and defines the concrete
corrections that must be implemented systematically.

**Scope**: Architecture violations and code quality only — no business logic changes,
no functional behavior modifications.

## Why

Applying changes directly led to repeated crashes because:
- Ad-hoc patch scripts ended up in commits (`fix_*.py`, `patch_*.py`)
- Services threw `fastapi.HTTPException` directly instead of domain exceptions
- Tests had permissive assertions (e.g., `500` as success status)
- Services executed SQL queries directly instead of delegating to repositories
- `assert` statements were used as runtime guards (disabled in production `-O` mode)

## Review Findings Summary

### 🔴 Critical (8 Findings)

| ID | File | Problem |
|----|-------|---------|
| CRITICAL-1 | `services/saved_trade_filter_service.py` | `HTTPException` directly in service (architecture violation) |
| CRITICAL-2 | `services/broker_service.py` | Direct SQLAlchemy queries in service instead of repository delegation |
| CRITICAL-3 | `services/import_service.py` | Direct SQLAlchemy queries in service |
| CRITICAL-4 | `services/flex_import_service.py` | Direct SQLAlchemy queries in service |
| CRITICAL-5 | `services/market_data_service.py` | All DB access in service, no `OhlcPriceRepository` exists |
| CRITICAL-6 | `services/account_service.py` L151, L194 | `assert` as runtime guard (unsafe in production `-O` mode) |
| CRITICAL-7 | `api/v1/executions.py` | Service constructed inline in every handler instead of DI; no `ResponseEnvelope`; `ReassignExecutionRequest` schema defined in API layer |
| CRITICAL-8 | `api/v1/cash_transactions.py` | Session passed directly to service static methods; missing `CashTransactionNotFoundError` handling (silent 500s) |

### 🟡 Warnings (37 Findings)

| ID | File | Problem |
|----|-------|---------|
| WARNING-1 | `services/trade_service.py` L27-52 | Class docstring placed after first method |
| WARNING-2 | `services/user_service.py` L151-152, L187-188 | Bare `except Exception` without logging |
| WARNING-3 | `services/user_service.py` L154 | `type: ignore` without justification comment |
| WARNING-4 | `services/flex_import_service.py` L38-39 | Magic numbers not in `constants.py` |
| WARNING-5 | `services/flex_import_service.py` L36-37 | Magic strings not in `constants.py` |
| WARNING-6 | `api/v1/imports.py` L37 | Magic number `_BYTES_PER_MB` not in `constants.py` |
| WARNING-7 | `api/v1/auth.py` L38 | Magic numbers in refresh token formula |
| WARNING-9 | `services/auth_service.py` L50, L73 | Service returns ORM model instead of Pydantic DTO |
| WARNING-10 | `services/auth_service.py` L148 | Service accepts ORM model as parameter |
| WARNING-11 | `services/cash_transaction_service.py` L32, L71, L107, L146, L212 | Service returns ORM models |
| WARNING-12 | `services/execution.py` L37, L56, L93, L152, L209 | Service returns ORM models |
| WARNING-13 | `services/market_data_service.py` L16 | Missing `-> None` type annotation |
| WARNING-14 | `services/execution.py` L1 | Missing module-level docstring |
| WARNING-15 | `services/cash_transaction_service.py` L1-4 | Minimal module docstring |
| WARNING-16 | `services/saved_trade_filter_service.py` L1 | Missing module docstring |
| WARNING-17 | `api/v1/trades.py` L593-600 | `merge_trades` route constructs service manually instead of DI |
| WARNING-18 | `api/v1/accounts.py` L266 | Magic number `404` instead of `status.HTTP_404_NOT_FOUND` |
| WARNING-19 | `api/v1/auth.py` L452, L621 | Fragile silent-no-op commit pattern in OAuth |
| WARNING-20 | `core/security.py` L190-191 | Unbounded in-memory set, no issue link |
| WARNING-21 | `core/security.py` L145 | Overly broad `except (JWTError, ValueError, Exception)` |
| WARNING-22 | `core/security.py` L180, L249 | Overly broad `except Exception` |
| WARNING-23 | `services/user_service.py` L142, L175 | `import json` inside method body |
| WARNING-24 | `services/timeseries_service.py` L178 | `import calendar` inside method body |
| WARNING-25 | `services/trade_service.py` L36, L74, L334, L367, L469 | Deferred imports without explanation comment |
| WARNING-26 | `services/trade_service.py` L371-484 | `partial_close_trade` never commits session |
| WARNING-27 | `services/trade_service.py` multiple | Access to private `_session` attribute of repository |
| WARNING-28 | `api/v1/trades.py` L153-156, L226-231 | DB queries (ownership check) directly in route handler |
| WARNING-29 | `api/v1/market_data.py` L36 | Mutable global `_http_client` not managed in lifespan (connection leak) |
| WARNING-30 | `api/v1/market_data.py` L73-84 | `response_model=None` with `Any` return type |
| WARNING-31 | `api/v1/market_data.py` L146, L157 | Magic status codes (`502`) as integer literal |
| WARNING-32 | `api/v1/screenshots.py` L86-109 | File I/O and URL construction directly in route handler |
| WARNING-33 | `api/v1/screenshots.py` L27 | `MAX_FILE_SIZE` magic constant not in `constants.py` |
| WARNING-34 | `api/v1/auth.py` L10 | `type: ignore[import-untyped]` without justification comment |
| WARNING-35 | `api/v1/broker.py` L65-67 | Query parameters without `Query()` annotation |
| WARNING-36 | `core/config.py` L137 | `Any` type in `parse_cors_origins` without justification comment |
| WARNING-37 | `core/database.py` L60 | `except Exception` re-raise without justification comment |

### 🔵 Suggestions (9 Findings)

| ID | File | Problem |
|----|-------|---------|
| SUGGESTION-1 | `services/saved_trade_filter_service.py` L12 | Minimal class docstring |
| SUGGESTION-2 | `services/cash_transaction_service.py` | Static method anti-pattern instead of instance service |
| SUGGESTION-3 | `services/account_service.py` L83 | TODO without issue link |
| SUGGESTION-4 | `api/v1/auth.py` L568 | One-liner docstring in `oidc_callback` |
| SUGGESTION-5 | `api/v1/trades.py` L598 | One-liner docstring in `merge_trades` |
| SUGGESTION-6 | `services/auth_service.py` L267-278 | Dead code (`_issue_token_pair` never called) |
| SUGGESTION-7 | `core/constants.py` L144-148 | Duplicate constant `NOTE_CONTENT_MAX_LENGTH` |
| SUGGESTION-8 | `services/tax_service.py` L25-26 | German strings without English explanation comment |
| SUGGESTION-9 | `api/v1/trades_update.py` | File's own docstring marks it as obsolete — delete |

## Acceptance Criteria

- No `fastapi.HTTPException` imports in `backend/app/services/*`
- No direct SQLAlchemy queries in services (all via repositories)
- No `assert` statements as runtime guards in services
- Services return Pydantic DTOs (no ORM objects to API layer)
- `partial_close_trade` commits correctly
- All module docstrings present and complete
- Temporary scripts (`fix_*.py`, `patch_*.py`, `update_*.py`) removed from repository
- Tests without permissive status code assertions (no `500` as success)
- `security.py` uses only `except (JWTError, ValueError)`
- `executions.py` uses DI pattern (`_get_service`) and `ResponseEnvelope` for all endpoints
- `cash_transactions.py` handles `CashTransactionNotFoundError` with `HTTP_404_NOT_FOUND`
- `_http_client` in `market_data.py` is managed in FastAPI lifespan
- No Pydantic schemas defined in `api/v1/` (only in `schemas/` layer)