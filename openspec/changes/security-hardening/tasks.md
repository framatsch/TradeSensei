## 1. Database Migration — OTT Blocklist Table

- [ ] 1.1 Create Alembic migration: `CREATE TABLE used_otts (jti TEXT PRIMARY KEY, expires_at TIMESTAMPTZ NOT NULL)`.
- [ ] 1.2 Add index: `CREATE INDEX ix_used_otts_expires ON used_otts(expires_at)`.
- [ ] 1.3 Create `UsedOtt` SQLAlchemy model in `backend/app/models/used_ott.py`.
- [ ] 1.4 Register model in `backend/app/models/__init__.py`.

## 2. OTT Blocklist — Backend

- [ ] 2.1 Add `consume_ott_jti(jti: str, expires_at: datetime, db: AsyncSession) -> bool` to `security.py`: INSERT with IntegrityError catch; DELETE expired rows in same call.
- [ ] 2.2 Replace all call sites of `_used_ott_jti.add(jti)` / `jti in _used_ott_jti` with `await consume_ott_jti(...)` calls.
- [ ] 2.3 Remove `_used_ott_jti: set[str]` module-level variable entirely.
- [ ] 2.4 Unit test: `test_ott_first_use_succeeds()` — insert succeeds, returns True.
- [ ] 2.5 Unit test: `test_ott_replay_rejected()` — second insert returns False.
- [ ] 2.6 Unit test: `test_ott_cleanup_deletes_expired()` — expired rows removed on consumption.
- [ ] 2.7 Unit test: `test_concurrent_ott_replay_safe()` — concurrent inserts of same JTI: exactly one succeeds.

## 3. Cursor Security

- [ ] 3.1 Add `encode_cursor(payload: dict, secret: str) -> str` to `app/core/security.py`: HMAC-SHA256 signed, base64url encoded.
- [ ] 3.2 Add `decode_cursor(token: str, secret: str) -> dict` to `app/core/security.py`: verifies signature; raises `ValueError` on mismatch.
- [ ] 3.3 Update `TradeRepository.list_cursor()`: encode outgoing cursor with `encode_cursor`; decode incoming cursor with `decode_cursor`; catch `ValueError` → raise `HTTPException(400, "invalid_cursor")`.
- [ ] 3.4 Audit all repository list methods with cursor: verify `AND user_id = :current_user_id` is present unconditionally (not just via filter dict).
- [ ] 3.5 Unit test: `test_cursor_encode_decode_roundtrip()`.
- [ ] 3.6 Unit test: `test_tampered_cursor_raises_400()`.
- [ ] 3.7 Unit test: `test_other_user_cursor_returns_empty()` — cursor from user A returns no rows when queried as user B.

## 4. CLI Password Fix

- [ ] 4.1 Remove `-p / --password` argument from `reset_password.py` argparse config.
- [ ] 4.2 Add `getpass.getpass()` interactive input with confirmation prompt (`New password:` / `Confirm password:`).
- [ ] 4.3 Add `sys.stdin.isatty()` branch for non-interactive (pipe) mode: read one line from stdin.
- [ ] 4.4 Add validation: if interactive and passwords do not match → print error, `sys.exit(1)`.
- [ ] 4.5 Update `add-password-reset-cli` tasks.md to remove the `-p` argument task (superseded here).
- [ ] 4.6 Manual test: interactive mode prompts correctly and hides input.
- [ ] 4.7 Manual test: `echo "newpw" | reset_password.py -u testuser` works non-interactively.

## 5. Exception Handling Cleanup in `security.py`

- [ ] 5.1 Find all `except (JWTError, ValueError, Exception)` clauses in `security.py` — replace with `except (JWTError, ValueError)`.
- [ ] 5.2 Find all legitimate re-raise patterns (`except Exception: ... rollback ... raise`) in `database.py` and related files — add comment `# Re-raise after rollback — caller sees original exception`.
- [ ] 5.3 Run mypy on `security.py` — must be clean.
- [ ] 5.4 Unit test: `test_unexpected_exception_propagates()` — mock JWT lib to raise AttributeError; verify it is not caught by auth handler.

## 6. Verification

- [ ] 6.1 Run full test suite — must be green.
- [ ] 6.2 Run `ruff` + `mypy` on changed files — must be clean.
- [ ] 6.3 Manual end-to-end: issue OTT, use it, attempt replay — verify 401 on replay.
- [ ] 6.4 Manual end-to-end: craft cursor with wrong HMAC, submit to `/trades` — verify 400.
- [ ] 6.5 Code review: confirm no remaining references to `_used_ott_jti` set.

## 7. Repository Pattern — Required `user_id`

- [ ] 7.1 Audit all repository classes: list every `get_by_id`, `update`, `delete` method that lacks a `user_id` parameter.
- [ ] 7.2 `TradeRepository`: add `user_id: int` to `get_by_id`, `update`, `delete`; add `AND Trade.user_id == user_id` to all WHERE clauses.
- [ ] 7.3 `ExecutionRepository`: same pattern — `get_by_id`, `update`, `delete`.
- [ ] 7.4 `AccountRepository`: same pattern.
- [ ] 7.5 `PlaybookRepository`: same pattern.
- [ ] 7.6 `TagRepository`: same pattern.
- [ ] 7.7 `NoteRepository`: same pattern.
- [ ] 7.8 `ScreenshotRepository`: same pattern.
- [ ] 7.9 `BrokerRawTransactionRepository`: same pattern.
- [ ] 7.10 Update all service call sites to pass `user_id=current_user.id` to every repository method updated above.
- [ ] 7.11 Verify all services raise `NotFoundError` (→ 404) when repository returns `None` — replace any `403` raises with `404`.

## 8. PostgreSQL Row-Level Security

- [ ] 8.1 Create Alembic migration: `ENABLE ROW LEVEL SECURITY` on `trades`, `logical_executions`, `broker_raw_transactions`, `accounts`, `playbooks`, `tags`, `trade_notes`, `screenshots`, `user_settings`.
- [ ] 8.2 In same migration: create `user_isolation` policy on each table: `USING (user_id = current_setting('app.current_user_id', true)::int)`.
- [ ] 8.3 Grant `BYPASSRLS` to the Alembic migration DB role.
- [ ] 8.4 Replace `get_db` dependency with `get_db_with_rls` on all authenticated routes: adds `SET LOCAL app.current_user_id = :uid` at transaction start.
- [ ] 8.5 Update `reset_password.py`: add `SET row_security = off` before password update query (or document running as superuser).
- [ ] 8.6 Verify Alembic migrations run cleanly with `BYPASSRLS` role.
- [ ] 8.7 Integration test: `test_rls_blocks_cross_user_raw_query()` — execute raw SQL as user A without `SET LOCAL`, verify user B's rows are not returned.
- [ ] 8.8 Integration test: `test_rls_correct_context_returns_own_rows()` — set `app.current_user_id`, verify correct rows returned.

## 9. UUID Primary Keys Audit

- [ ] 9.1 Audit all user-facing resource tables: document which use integer PKs vs UUID PKs.
- [ ] 9.2 For any table using integer PKs on user-facing resources: create Alembic migration to `UUID DEFAULT gen_random_uuid()`.
- [ ] 9.3 Update all FK references to changed PK columns.
- [ ] 9.4 Update all Pydantic schemas and API path parameters to `UUID` type.
- [ ] 9.5 Verify no sequential integer IDs appear in any API response for user-facing resources.

## 10. Ownership Tests

- [ ] 10.1 Add `other_user` fixture to `backend/tests/conftest.py`.
- [ ] 10.2 Add `other_users_trade` fixture.
- [ ] 10.3 Add `other_users_execution` fixture.
- [ ] 10.4 Add `other_users_account` fixture.
- [ ] 10.5 Add `other_users_playbook` fixture.
- [ ] 10.6 Add `other_users_tag` fixture.
- [ ] 10.7 Add `other_users_note` fixture.
- [ ] 10.8 Add `other_users_screenshot` fixture.
- [ ] 10.9 Add `other_users_brt` (BrokerRawTransaction) fixture.
- [ ] 10.10 Write `test_trade_ownership.py`: GET/PATCH/DELETE each assert `status_code == 404`.
- [ ] 10.11 Write `test_execution_ownership.py`: GET/PATCH/DELETE.
- [ ] 10.12 Write `test_account_ownership.py`: GET/PATCH/DELETE.
- [ ] 10.13 Write `test_playbook_ownership.py`: GET/PATCH/DELETE.
- [ ] 10.14 Write `test_tag_ownership.py`: GET/PATCH/DELETE.
- [ ] 10.15 Write `test_note_ownership.py`: GET/PATCH/DELETE.
- [ ] 10.16 Write `test_screenshot_ownership.py`: GET/PATCH/DELETE.
- [ ] 10.17 Write `test_brt_ownership.py`: GET/PATCH.
- [ ] 10.18 Verify all 24+ ownership tests pass and are included in CI.
