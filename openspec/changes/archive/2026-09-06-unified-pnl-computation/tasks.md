## 1. Baseline and Pre-Flight

- [x] 1.1 Start the test database: `docker compose -f docker-compose.test.yml up -d` (integration tests need Postgres on port 5433 per `backend/tests/conftest.py:32`)
- [x] 1.2 Record the green baseline: `uv run pytest tests/test_execution_api.py tests/test_execution_reaggregation.py tests/test_execution_service.py -q` — expect 47 passed
- [ ] 1.3 Run the deviation scan from `design.md` against production; confirm 0 rows before changing anything
- [x] 1.4 Run the deviation scan against local; confirm exactly 2 rows (DIOD, TGT)
- [x] 1.5 Confirm zero orphan trades in both databases: `SELECT count(*) FROM trades WHERE entry_price = 0.001`

## 2. Characterisation Tests (write first, expect failures)

- [x] 2.1 Add a failing test: re-aggregating a non-combo trade whose closing leg carries `pnl = Decimal("0")` (Schwab sentinel) must produce price-derived P&L, not zero
- [x] 2.2 Add a failing test: re-aggregating a non-combo trade whose legs carry net-of-commission broker P&L must produce gross `pnl`, with `net_pnl = pnl - commission` deducted exactly once
- [x] 2.3 Add a failing test: a split child holding the parent's full unprorated `pnl` must not influence the re-aggregated trade P&L
- [x] 2.4 Add an equivalence test asserting `_re_aggregate_trade` and `aggregate_executions_fifo` produce identical `pnl`, `net_pnl`, `entry_price`, `exit_price`, `quantity` and `commission` for the same executions (extend the existing pattern at `tests/test_execution_service.py:920-970`, which currently asserts only `net_pnl`)
- [x] 2.5 Confirm all four fail against current `main` for the expected reason, not by accident

## 3. Implementation

- [x] 3.1 In `backend/app/services/execution.py:1110-1120`, remove the `has_broker_pnl` preference from the non-combo branch so gross P&L is always computed from `(exit − entry) × qty × multiplier`
- [x] 3.2 Keep `has_broker_pnl` and `total_pnl` intact — the combo branch at `:1080-1083` still uses them; confirm no unused-variable lint error results
- [x] 3.3 Update the comment at `:1107` ("prefer sum of broker-reported pnl") to state the new rule and reference the `pnl-calculation` capability
- [x] 3.4 Verify the tests from section 2 now pass

## 4. Regression Coverage For The Reported Scenario

- [x] 4.1 Add an integration test that merges two Schwab trades end to end and asserts price-derived P&L — the exact scenario that produced the report and is currently untested
- [x] 4.2 Add a unit test pinning the Schwab parser's `pnl = Decimal("0")` sentinel for `positionEffect = CLOSING`, documenting it as a closing-leg marker (no such test exists in `tests/test_schwab_json_parser.py`)
- [x] 4.3 Add coverage for at least two further mutation paths beyond merge — e.g. execution delete/restore and execution split — asserting P&L stays price-derived

## 5. Verification

- [x] 5.1 Run the full backend suite; confirm no regressions beyond intentionally updated tests
- [x] 5.2 Confirm no test asserting the non-combo broker-P&L preference had to be weakened or deleted; if one did, stop and reassess — it would mean the behaviour was intentional
- [x] 5.3 Run `lint-check` (ruff + `mypy --strict`)
- [x] 5.4 Re-run the deviation scan on local; confirm still exactly 2 rows (the fix prevents new corruption but does not retroactively repair stored values)

## 6. Data Correction (local dev only)

- [x] 6.1 Clear the unprorated `pnl` on the TGT split leg (`origin='split'`, `quantity=1`, `pnl=-65.84390`) — otherwise re-aggregation reproduces the error
- [x] 6.2 Re-aggregate DIOD `c76fd9c6-0e09-4934-ad53-729222977cc2` via `re_aggregate_trade`; expect `pnl` `0.00 → -133.90`
- [x] 6.3 Re-aggregate TGT `91cd12e5-d282-4aa3-8bff-e6442e157705` via `re_aggregate_trade`; expect `pnl` `-65.84390 → -62.84`
- [x] 6.4 Re-run the deviation scan on local; expect 0 rows
- [ ] 6.5 Re-run the deviation scan on production; expect 0 rows (no production correction should be required)

## 7. Documentation and Follow-Ups

- [x] 7.1 Record the deferred combo gross/net defect with the supporting data from `design.md`, including the two tests that pin current behaviour
- [x] 7.2 Record the `import_service.py:2015` unprorated-split-P&L defect and its divergence from `execution.py:661/681/802`
- [x] 7.3 Record the `open_close` prerequisites from Decision 2 (missing backfill, absent from `LogicalExecutionCreate`/`Update`, not propagated by user split/merge) for whoever makes it authoritative
- [x] 7.4 Record the `aggregator.py:767` EUR-conversion guard and the ATOS over-linking anomaly
- [x] 7.5 Delete `tmp/pnl-reaggregation-bug.md` once this change carries the analysis
