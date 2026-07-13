## 1. Backend — Adjustment Helper

- [x] 1.1 Add a pure `Decimal` helper (e.g. `app/utils/split_adjust.py`) computing `adjusted_price = raw_price / ∏ratio` and `adjusted_quantity = raw_quantity × ∏ratio` for a leg given the applicable `CorporateAction` rows; document linkage to `aggregator.py:677` (`_apply_split_event`).
- [x] 1.2 Implement CA-to-leg matching: select CAs where `symbol` matches (or conid ∈ {old_conid, new_conid}) AND `ca.date > executed_at` (date-only, UTC); compound multiple ratios in chronological order.
- [x] 1.3 Handle no-CA / manual case: return stored values unchanged (adjusted == raw).

## 2. Backend — Schema & Service

- [x] 2.1 Extend `LogicalExecutionRead` (`app/schemas/execution.py:208`) with `raw_price: Decimal` and `raw_quantity: Decimal` (field descriptions for OpenAPI).
- [x] 2.2 In `ExecutionService.list_for_trade` (`app/services/execution.py`), load the user's CAs once via `CorporateActionService.list_for_aggregator`, apply the helper per leg, populate `price`/`quantity` (adjusted) and `raw_price`/`raw_quantity` (stored originals).
- [x] 2.3 Confirm `list_trade_executions` (`app/api/v1/executions.py:59`) returns the enriched schema by default with no new required query param; keep `include_deleted` behavior intact.
- [x] 2.4 Verify audit-logging policy: read-only GET requires no new audit event; confirm no sensitive fields added to logs.

## 3. Frontend — API Client & Markers

- [x] 3.1 Run `/openapi-sync` to regenerate the TypeScript client with `raw_price`/`raw_quantity`.
- [x] 3.2 Update the trade chart marker component to position markers at the adjusted price (`price`) and render label `<adjusted> (raw: <raw>)`; drop the `(raw: …)` suffix when adjusted == raw. Reuse the existing currency formatter.

## 4. Tests

- [x] 4.1 Backend unit test — adjusted values scaled correctly for a pre-split trade; assert `raw_*` equal stored `LogicalExecution` values (`tests/services/test_execution*.py`).
- [x] 4.2 Backend unit test — multiple sequential splits compound; single-value case with no CA (adjusted == raw).
- [x] 4.3 Backend unit test — `origin='manual'` leg fallback (no CA → adjusted == raw; with applicable CA → adjusted differs, raw retained).
- [x] 4.4 Backend invariant test — `price × quantity` (adjusted) equals `raw_price × raw_quantity` within Decimal tolerance.
- [x] 4.5 Frontend component test — dual-value marker label renders both values when adjusted ≠ raw and a single value when equal.

## 5. Verification & Review

- [x] 5.1 Run `/lint-check` (ruff + mypy --strict) and `/unit-test` (pytest with coverage); all green.
- [x] 5.2 `code-reviewer` pass — architecture compliance, Decimal usage, additive/non-breaking schema, audit policy.
- [x] 5.3 `docs-writer` — update `api-usage.md` for the new `raw_*` fields; `changelog-writer` — append to `[Unreleased]`.
