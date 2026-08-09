## Context

Trade Sensei aggregates broker executions into matched trades via FIFO. Corporate actions — currently only forward and reverse splits — change the share count and price of positions that are held across the action's effective date.

Three independent implementations of the same split arithmetic exist today, and they disagree:

| Implementation | Scoping | Which positions it adjusts | Commission |
|---|---|---|---|
| `aggregator.py:_apply_split_event` | symbol + `old_conid` | only lots still open when the effective date is crossed | scaled by ratio |
| `execution.py:_re_aggregate_trade` | symbol only (`conid=None`) | every execution before the effective date | not scaled |
| `utils/split_adjust.py` | symbol + conid, UTC-normalised | every execution before the effective date | n/a |

The divergence is observable in production data. Trades in `OTLK` opened 2023-05-22 and closed 2023-05-24, with a 1:20 reverse split effective 2024-03-13, are persisted with raw values (`quantity=69`, `entry_price=1.44`) because the aggregator correctly leaves closed positions alone. `_re_aggregate_trade` would rewrite them to `quantity=3.45`, `entry_price=28.80`. Since corporate action CRUD triggers re-aggregation for the whole symbol, editing the split's date would silently corrupt all 22 `OTLK` trades.

A second inconsistency is already live: `GET /trades/{id}/executions` returns split-adjusted leg values while the `Trade` header returns historical values, so legs no longer sum to the header in the same response.

## Goals / Non-Goals

**Goals:**

- One shared implementation of split arithmetic, with the holding-period rule as the single definition of which positions an action affects.
- Persisted trade values represent what actually happened in the account; chart alignment is a separate, explicitly labelled basis.
- Corporate action CRUD is safe to invoke: it never produces values that a broker import would not also produce.
- Users can see that a trade is affected by a corporate action instead of inferring it from mismatched numbers.

**Non-Goals:**

- Corporate actions other than splits and reverse splits. Spinoffs, mergers, stock dividends, and delistings are out of scope; the model has no action type and none is added here.
- Automatically repairing FIFO matching boundaries that were built without a prerequisite corporate action. Detection and surfacing of that state is deferred to a follow-up decision (see Open Questions).

## Decisions

**1. The holding-period rule is canonical; the aggregator's semantics win**

A corporate action adjusts a position only if the position was open across the effective date. A position opened and closed entirely before the effective date was never subject to the action.

*Rationale:* This is historical truth. The account statement says 69 shares at $1.44, and realised PnL must reflect that. It is also the semantics already encoded in the persisted production data, so no backfill is required and no historical performance number changes.

*Alternative considered:* Adopting `_re_aggregate_trade`'s rule — adjust everything before the effective date. Rejected because it restates already-realised trades, changing reported historical performance, and would require migrating existing rows.

*Consequence:* `_re_aggregate_trade` is the implementation that changes. Its unconditional loop is replaced by a call into the shared helper.

**2. Commission is never adjusted by a split ratio**

*Rationale:* Commission is a currency amount. A 1:20 reverse split does not retroactively reduce the fee that was paid. The aggregator currently scales it, which is the reason `net_pnl` differs depending on whether a trade came from an import or from re-aggregation.

*Consequence:* `_apply_split_event` stops scaling `commission` and `source_commission`. This does change `net_pnl` for any trade held across a split — a small set, and in the direction of correctness. Requires a verification pass against `tests/integration/ground_truth_aggregator.py` before and after.

**3. The trade projection is rebuilt from `LogicalExecution`; seed lots are removed**

The FIFO seed-lot mechanism preloads persisted open trades whose quantities are already split-adjusted, then replays every historical corporate action against them. `test_aggregator_seed_lots.py:113` passes only because its seed carries raw quantities — an assumption that the requirement to persist adjusted values invalidates.

*Rationale:* Keeping both would require a per-trade adjustment watermark, which is state that only exists to compensate for a redundant code path. Rebuilding from the immutable logical layer is consistent with the stated source-of-truth model and is what the raw pipeline already does (`import_service.py:488` passes `seed_open_lots=None`).

*Cost: none.* The only parser without `parse_raw` is `SchwabParser` (`schwab.py`, CSV/XLSX), and it is unreachable from production code — `factory.py:48-51` wires `BrokerType.SCHWAB` to `SchwabJSONParser`. Its sole remaining references are its own definition and `test_import.py:112-174`; the module-private helpers `_parse_decimal` and `_parse_schwab_date` are used nowhere else. Schwab transactions arrive as JSON. `SchwabParser` is therefore deleted rather than ported, which makes the legacy branch at `import_service.py:500-508` unreachable and lets seed lots go with it.

*Rebuild cost is negligible at current scale:* 1048 logical executions, 453 trades. FIFO is a sort plus a linear scan, entirely in memory.

*Alternative considered:* Persist a `split_adjusted_through` watermark on `Trade` and only apply later actions to seeds. Rejected as complexity that exists solely to keep a second aggregation path alive.

**4. Two explicit bases, never mixed**

Persisted trade values use the historical basis. Chart-adjusted values are derived on read, applying every action later than the execution — mirroring how providers restate historical bars.

*Rationale:* Both are correct for their purpose, and the existing execution read path already does this well: legs expose adjusted `price`/`quantity` plus `raw_price`/`raw_quantity`, and `executionPriceLabel.ts` renders `"$28.80 (raw: $1.44)"`. The gap is that this stopped at the leg level — the trade header has no adjusted counterpart and no marker.

*Consequence:* `Trade` gains chart-adjusted counterparts and an affected-by-corporate-action marker. The invariant "legs sum to header" must hold within each basis.

**5. Corporate action changes invalidate cached price bars by deletion**

`ohlc_prices` has no adjustment basis recorded and a unique constraint on `(symbol, interval, provider, start)`, so cached bars are never overwritten. Bars cached before a split keep the pre-split basis forever while bars fetched afterwards arrive adjusted, producing a discontinuity at the effective date.

*Rationale:* Deleting the symbol's bars is a few lines and reuses the refetch path already specified by `chart-cache-refresh` (`force_refresh`, global cache clear). The cache is fully reconstructible.

*Alternative considered:* An `adjusted_through` column on `ohlc_prices` with basis-aware fetching. Rejected — a migration plus fetch-path logic for an event that occurs perhaps once per symbol per several years.

**6. The effective-date boundary uses the exchange-local calendar date**

*Rationale:* US regular hours (09:30–16:00 ET) fall on the same calendar day in both ET and UTC, so the choice looks irrelevant — but extended-hours executions from roughly 19:00 ET onward roll over into the next UTC day. An after-hours purchase on the evening before a reverse split would then carry the effective date as its UTC date, be classified as post-split, and go unadjusted. That is a realistic trading pattern, not a constructed edge case.

*Constraint:* `LogicalExecution` has no exchange field. Only `currency` is available (1046 of 1048 rows are `USD`, 2 are `NULL`), so the exchange cannot be resolved from stored data today.

*Consequence:* The specification fixes the correct semantics — exchange-local date. The implementation resolves the instrument's timezone and, until an exchange field exists, applies a documented default of `America/New_York` for USD-denominated instruments. The approximation is recorded rather than hidden, and adding an exchange or timezone field to `LogicalExecution` is tracked as a follow-up.

*Alternative considered:* Keeping UTC because the data is effectively all US equities. Rejected — it bakes a US assumption into the semantics, and the after-hours window is exactly where a split-related error would occur.

**7. Corporate actions are unique per user, symbol, and effective date**

*Rationale:* The manual create path performs no deduplication at all; only the import path does, via `find_by_user_symbol_date_ratio`. Creating the same split twice applies its ratio twice, which for `ATOS` would turn a 1:15 reverse split into 1:225.

The uniqueness key deliberately excludes `ratio`. Including it — as the current import deduplication does — means a mistyped ratio (`0.0666667` versus `0.06666667`) creates a second row instead of failing, and both are then applied. The key is `(user_id, symbol, date)`.

*Conflict behaviour:* manual create returns a conflict identifying the existing record so the user edits it; import updates the existing record, because the broker file is the authoritative source and the user can review the result afterwards.

*Migration risk: none.* Two corporate actions exist, with no duplicates.

**8. Corporate action changes are atomic, and recalculation is idempotent**

Corporate action CRUD, trade recalculation, and price-cache invalidation run in a single transaction with one commit. Today `create_corporate_action` commits the action, then recalculates, then commits again — a failure in between leaves the action persisted alongside half-rewritten trades, and because of the missing uniqueness constraint the user's natural retry creates a second action.

*Rationale for a single transaction rather than a background job:* the largest symbol holds 194 trades, so transaction duration is not a concern and lock contention is not a realistic risk at this scale.

*Idempotency is the load-bearing property:* with the holding-period rule and the rebuild from `LogicalExecution`, recalculation derives values from immutable raw data and the current action set rather than mutating previously computed values. Repeated runs converge on the same result, which is what makes a retry after rollback safe and what makes CRUD-triggered rebuilds safe in general. It is specified as a requirement, not left as an implementation detail.

## Risks / Trade-offs

- **[Risk]** Decision 2 changes `net_pnl` for trades held across a split. → **Mitigation:** capture ground-truth output before the change, diff after, and confirm every delta is explained by a commission that is no longer scaled.
- **[Risk]** Deleting `SchwabParser` removes a fallback for CSV/XLSX input. → **Mitigation:** confirmed unreachable — `factory.py` never constructs it and Schwab transactions arrive as JSON. If CSV import is ever wanted again it must be built on `parse_raw`, not resurrected.
- **[Risk]** The `America/New_York` default for the effective-date boundary is wrong for non-US instruments. → **Mitigation:** all current holdings are USD-denominated. The default is documented in code, and any non-US instrument must trigger the follow-up that adds an exchange field rather than silently inheriting the default.
- **[Risk]** Consolidating three implementations into one may change values in paths not covered by tests. → **Mitigation:** `tests/integration/ground_truth_aggregator.py`, `test_pnl_regression.py`, `test_aggregator_synthetic_fixture.py` (SPLK reverse split across a year boundary) and `test_aggregator_seed_lots.py` form the regression net. `test_aggregator_seed_lots.py:113` must be rewritten, not deleted, when seed lots are removed.
- **[Trade-off]** The holding-period rule means a chart of a closed pre-split trade shows entry markers on a different basis than the trade header. This is inherent to the two-basis model and is why the marker from Decision 4 is mandatory rather than cosmetic.

## Open Questions

Deliberately not decided in this change; each needs its own call before implementation of the affected area.

1. **Ratio representation.** `ratio` is a single `Decimal`. A 1:15 reverse split is stored as `0.06666667` (production: `ATOS`), which cannot represent 1/15 exactly, so `quantity * ratio` and `price / ratio` both carry error that compounds across sequential actions. Storing the ratio as a rational pair of integers would make the notional-preservation invariant exact. Until decided, no exact invariant can be asserted.
2. **Fractional shares and cash-in-lieu.** A 1:15 reverse split of 100 shares yields 6.67 shares; brokers round down and pay cash in lieu. No rounding policy exists and no cash leg is modelled.
3. **Detection of broken matching boundaries.** When executions were imported without their prerequisite corporate action, FIFO may produce spurious positions. Nothing detects or surfaces this; the `Trade.has_conflict` mechanism is a candidate carrier.
4. **Scope of application.** Recalculation resolves affected trades by exact symbol match only, ignoring the `old_conid`/`new_conid` lineage the model exists to support, ignoring asset class, and with no time bound against ticker reuse.
5. **Exchange field on `LogicalExecution`.** Decision 6 fixes exchange-local semantics but must approximate the timezone, because no exchange is stored. Adding the field — and having the parsers populate it — removes the approximation.
6. **`source_qty_factor` is not persisted.** The aggregator maintains it and divides by it for allocation, but `Trade` has no such column and seed preloading defaults it to 1. Resolved by Decision 3; listed here so it is re-examined if seed lots ever return.
