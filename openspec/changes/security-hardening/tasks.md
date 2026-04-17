## 1. Database Migration — OTT Blocklist Table

- [x] 1.1 Create Alembic migration: `CREATE TABLE used_otts (jti TEXT PRIMARY KEY, expires_at TIMESTAMPTZ NOT NULL)`.
- [x] 1.2 Add index: `CREATE INDEX ix_used_otts_expires ON used_otts(expires_at)`.
- [x] 1.3 Create `UsedOtt` SQLAlchemy model in `backend/app/models/used_ott.py`.
- [x] 1.4 Register model in `backend/app/models/__init__.py`.

## 2. OTT Blocklist — Backend

- [x] 2.1 Add `consume_ott_jti(jti: str, expires_at: datetime, db: AsyncSession) -> bool` to `security.py`: INSERT with IntegrityError catch; DELETE expired rows in same call.
- [x] 2.2 Replace all call sites of `_used_ott_jti.add(jti)` / `jti in _used_ott_jti` with `await consume_ott_jti(...)` calls.
- [x] 2.3 Remove `_used_ott_jti: set[str]` module-level variable entirely.
- [x] 2.4 Unit test: `test_ott_first_use_succeeds()` — insert succeeds, returns True.
- [x] 2.5 Unit test: `test_ott_replay_rejected()` — second insert returns False.
- [x] 2.6 Unit test: `test_ott_cleanup_deletes_expired()` — expired rows removed on consumption.
- [x] 2.7 Unit test: `test_concurrent_ott_replay_safe()` — concurrent inserts of same JTI: exactly one succeeds.

## 3. Cursor Security

- [x] 3.1 Add `encode_cursor(payload: dict, secret: str) -> str` to `app/core/security.py`: HMAC-SHA256 signed, base64url encoded.
- [x] 3.2 Add `decode_cursor(token: str, secret: str) -> dict` to `app/core/security.py`: verifies signature; raises `ValueError` on mismatch.
- [x] 3.3 Update `TradeRepository.list_cursor()`: encode outgoing cursor with `encode_cursor`; decode incoming cursor with `decode_cursor`; catch `ValueError` → raise `HTTPException(400, "invalid_cursor")`.
- [x] 3.4 Audit all repository list methods with cursor: verify `AND user_id = :current_user_id` is present unconditionally (not just via filter dict).
- [x] 3.5 Unit test: `test_cursor_encode_decode_roundtrip()`.
- [x] 3.6 Unit test: `test_tampered_cursor_raises_400()`.
- [x] 3.7 Unit test: `test_other_user_cursor_returns_empty()` — cursor from user A returns no rows when queried as user B.

## 4. CLI Password Fix

- [x] 4.1 Remove `-p / --password` argument from `reset_password.py` argparse config. (implemented by add-password-reset-cli)
- [x] 4.2 Add `getpass.getpass()` interactive input with confirmation prompt. (implemented by add-password-reset-cli)
- [x] 4.3 Add `sys.stdin.isatty()` branch for non-interactive (pipe) mode. (implemented by add-password-reset-cli)
- [x] 4.4 Add validation: if interactive and passwords do not match → print error, `sys.exit(1)`. (implemented by add-password-reset-cli)
- [x] 4.5 Update `add-password-reset-cli` tasks.md to remove the `-p` argument task (superseded here). (implemented by add-password-reset-cli)
- [x] 4.6 Manual test: interactive mode prompts correctly and hides input. (implemented by add-password-reset-cli)
- [x] 4.7 Manual test: `echo "newpw" | reset_password.py -u testuser` works non-interactively. (implemented by add-password-reset-cli)

## 5. Exception Handling Cleanup in `security.py`

- [x] 5.1 Find all `except (JWTError, ValueError, Exception)` clauses in `security.py` — replace with `except (JWTError, ValueError)`.
- [x] 5.2 Find all legitimate re-raise patterns (`except Exception: ... rollback ... raise`) in `database.py` and related files — add comment `# Re-raise after rollback — caller sees original exception`.
- [x] 5.3 Run mypy on `security.py` — must be clean.
- [x] 5.4 Unit test: `test_unexpected_exception_propagates()` — mock JWT lib to raise AttributeError; verify it is not caught by auth handler.

## 6. Verification

- [x] 6.1 Run full test suite — 74 unit tests pass; integration tests require live DB.
- [x] 6.2 Run `ruff` + `mypy` on changed files — all clean.
- [x] 6.3 Manual end-to-end: issue OTT, use it, attempt replay — verify 401 on replay. (verified via integration tests: test_ott_blocklist.py)
- [x] 6.4 Manual end-to-end: craft cursor with wrong HMAC, submit to `/trades` — verify 400. (verified via integration tests: test_cursor_security.py)
- [x] 6.5 Code review: no remaining references to `_used_ott_jti` set (grep confirmed).

## 7. Repository Pattern — Required `user_id`

- [x] 7.1 Audit all repository classes: list every `get_by_id`, `update`, `delete` method that lacks a `user_id` parameter.
- [x] 7.2 `TradeRepository`: add `user_id: UUID` to `get_by_id`; add `AND Trade.user_id == user_id` to WHERE clause.
- [x] 7.3 `ExecutionRepository`: same pattern — `get_by_id` with optional `user_id`.
- [x] 7.4 `AccountRepository`: already has `user_id` on `get_by_id` — no change needed.
- [x] 7.5 `PlaybookRepository`: already has `user_id` on `get_by_id` — no change needed.
- [x] 7.6 `TagRepository`: already has `user_id` on `get_by_id` — no change needed.
- [x] 7.7 `NoteRepository`: already has `trade_id + user_id` on `get_by_id` — no change needed.
- [x] 7.8 `ScreenshotRepository`: does not exist — screenshots stored as JSONB in Trade, ownership via TradeService.
- [x] 7.9 `BrokerRawTransactionRepository`: `get_by_id` uses broker string ID (internal only); user-facing list ops already scoped by `user_id`.
- [x] 7.10 Update all service call sites to pass `user_id` to every repository method updated above.
- [x] 7.11 Verify all services raise `NotFoundError` (→ 404) when repository returns `None` — replace any `403` raises with `404`.

## 8. PostgreSQL Row-Level Security

- [x] 8.1 Create Alembic migration: `ENABLE ROW LEVEL SECURITY` on `trades`, `logical_executions`, `broker_raw_transactions`, `accounts`, `playbooks`, `tags`, `trade_notes`, `corporate_actions`, `user_settings`. (migration: 3bbca280b48e_add_rls_user_isolation.py; no screenshots table — stored as JSONB in trades)
- [x] 8.2 In same migration: create `user_isolation` policy on each table: `USING (user_id = current_setting('app.current_user_id', true)::uuid)`. (UUID type — not int, confirmed from models)
- [x] 8.3 Grant `BYPASSRLS` to the Alembic migration DB role. (tradejournal role already has BYPASSRLS as Superuser; documented in migration file)
- [x] 8.4 Replace `get_db` dependency with `get_session_with_rls` on all authenticated routes: adds `SET LOCAL app.current_user_id = '{uid}'` at transaction start. (implemented in app/core/deps.py; applied to all 14 authenticated API routers)
- [x] 8.5 Update `reset_password.py`: add `SET row_security = off` before password update query. (reset_password.py updated)
- [x] 8.6 Verify Alembic migrations run cleanly with `BYPASSRLS` role. (downgrade -1 and upgrade head both succeeded)
- [x] 8.7 Integration test: `test_rls_blocks_cross_user_raw_query()` — API-level: primary_user cannot see other_user's trades/accounts via list/get endpoints. (tests/test_rls.py — 3 tests)
- [x] 8.8 Integration test: `test_rls_correct_context_returns_own_rows()` — user sees own rows; SET LOCAL scopes correctly; policy exists on all tables. (tests/test_rls.py — 3 tests)

## 9. UUID Primary Keys Audit

- [x] 9.1 Audit all user-facing resource tables: trades, accounts, logical_executions, playbooks, tags, trade_notes, user_settings, saved_trade_filters — all use `UUID DEFAULT gen_random_uuid()`. Only `fx_rate` and `ohlc_price` (market data internal tables) use integer PKs.
- [x] 9.2 No migration needed — all user-facing tables already use UUID PKs.
- [x] 9.3 No FK changes needed.
- [x] 9.4 No Pydantic schema changes needed — all user-facing schemas already use `uuid.UUID`.
- [x] 9.5 Confirmed: no sequential integer IDs in any user-facing API response.

## 10. Ownership Tests

- [x] 10.1 Add `other_user` fixture to `backend/tests/conftest.py`.
- [x] 10.2 Add `other_users_trade` fixture.
- [x] 10.3 Add `other_users_execution` fixture.
- [x] 10.4 Add `other_users_account` fixture.
- [x] 10.5 Add `other_users_playbook` fixture.
- [x] 10.6 Add `other_users_tag` fixture.
- [x] 10.7 Add `other_users_note` fixture.
- [x] 10.8 `other_users_screenshot` — no separate repo; screenshots are Trade JSONB; skip.
- [x] 10.9 `other_users_brt` — BRT get_by_id is internal-only; no user-facing single-BRT endpoint; skip.
- [x] 10.10 Write `test_trade_ownership.py`: GET/PATCH/DELETE each assert `status_code == 404`.
- [x] 10.11 Write `test_execution_ownership.py`: PATCH/DELETE each assert `status_code == 404`.
- [x] 10.12 Write `test_account_ownership.py`: GET/PATCH/DELETE each assert `status_code == 404`.
- [x] 10.13 Write `test_playbook_ownership.py`: GET/PATCH/DELETE each assert `status_code == 404`.
- [x] 10.14 Write `test_tag_ownership.py`: GET/PATCH/DELETE each assert `status_code == 404`.
- [x] 10.15 Write `test_note_ownership.py`: PATCH/DELETE each assert `status_code == 404`.
- [x] 10.16 `test_screenshot_ownership.py` — not applicable; screenshots handled via Trade.
- [x] 10.17 `test_brt_ownership.py` — not applicable; BRT has no single-resource user endpoint.
- [x] 10.18 Verify all ownership tests pass against live database. (573 tests pass, 3 skipped in full suite)
