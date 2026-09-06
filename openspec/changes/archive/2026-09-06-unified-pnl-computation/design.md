## Context

Two code paths derive a `Trade`'s P&L from its executions:

| | Path | Rule applied |
|---|---|---|
| Import | `aggregate_executions_fifo` (`aggregator.py:663`, `:754-764`) | broker `pnl` used **only as a boolean gate**; gross P&L always `(exit − entry) × qty × multiplier` |
| Re-aggregation | `ExecutionService._re_aggregate_trade` (`execution.py:1061-1065`, `:1107-1120`) | broker `pnl` summed and **preferred as the value**; price computation is the fallback |

`2026-04-18-fix-ibkr-pnl-calculation` established the first rule and stated it explicitly:
*"The `pnl` field in `LogicalExecution` will remain, but it will be ignored during the
aggregation to `Trade`."* The aggregator was changed accordingly. `_re_aggregate_trade` was
not. The `pnl-calculation` capability that change declared was never materialised into
`openspec/specs/`, so no spec existed against which the divergence could be checked.

### How the divergence surfaces

**Schwab** — `schwab_json.py:180` sets `pnl = Decimal("0")` for every closing leg. Schwab
reports no realised P&L; the `0` exists solely so `aggregator.py:663` can detect a closing
leg. `logical_execution_service.py:114` copies it verbatim into the database, so it is a
persisted column value, not an in-memory flag. In `_re_aggregate_trade` the sentinel passes
`ex.pnl is not None`, sets `has_broker_pnl = True` and `total_pnl = 0`, and the price
computation at `:1114-1120` is skipped.

Observed: merging two DIOD trades produced `pnl = 0.00`, `net_pnl = -0.02`, against a correct
`(94.75 − 108.14) × 10 = −133.90`.

**IBKR** — `fifoPnlRealized` is *net of commission*. Measured across all 259 closed non-combo
IBKR trades in local dev data:

```
Σ leg.pnl == trade.net_pnl   →  258 / 259
```

So the broker-P&L branch assigns a **net** figure to `trade.pnl`, after which
`execution.py:1123` subtracts commission a second time. The single exception, ATOS, is an
unrelated over-linking defect (1250 leg-shares attached to a 200-share trade).

The local TGT trade is already wrong for a compounding reason: `import_service.py:2015`
copies the parent's **full unprorated** P&L onto the first split child, so a 1-share leg
carries a 20-share P&L. Stored `−65.8439` against a correct `−62.84`; the difference of
`3.0039` is exactly the sum of commissions. `execution.py:661/681/802` (user-driven split and
merge) correctly set `pnl=None` — the two split implementations disagree.

### Current exposure

| | local | production |
|---|---|---|
| Trades total | 450 | 452 |
| Already miscalculated | 2 (DIOD, TGT) | **0** |
| IBKR closed non-combo with leg P&L | 259 | — |
| Schwab trades / closed | 9 / 7 | — |
| Orphan trades (`entry_price = 0.001`) | 0 | 0 |

Production is clean. The exposure is latent: 25 call sites reach `_re_aggregate_trade`, so any
leg create/update/delete/split/merge/reassign/restore, any trade merge, and any
corporate-action replay converts a correct trade into an incorrect one.

## Goals / Non-Goals

**Goals:**
- Make re-aggregation reproduce import for identical executions.
- Bring `_re_aggregate_trade` into compliance with the rule accepted in April 2026.
- Materialise `pnl-calculation` as a living, enforceable capability.
- Cover the regression that produced the report: merging a Schwab trade.
- Correct the two locally miscalculated trades.

**Non-Goals:**
- Changing the combo P&L branch (`execution.py:1080-1083`, `aggregator.py:327-328`).
- Prorating broker P&L across split children in `import_service.py`.
- Backfilling or repairing `open_close`.
- Changing `LogicalExecution.pnl` values, the Schwab parser, or any schema.
- The ATOS over-linking defect.

## Decisions

### 1. Delete the broker-P&L branch from the non-combo path; do not try to validate the value

`execution.py:1110-1120` becomes an unconditional price computation. `has_broker_pnl` and
`total_pnl` stay — the combo branch at `:1080-1083` still uses them.

*Rationale:* the value is unusable from both brokers, for different reasons — Schwab's is
fabricated, IBKR's is net-of-commission and unprorated across splits. There is no broker whose
value is currently correct to prefer, so preferring it has no upside. Deleting the branch is
also what makes re-aggregation equal import, which is the actual requirement.

*Alternatives considered:*
- **Distinguish sentinel from real value** (e.g. by broker type, or `pnl == 0 and open_close == 'C'`).
  Rejected: it preserves the IBKR net/gross bug, and it entrenches `pnl` as a dual-purpose
  field. It also cannot separate Schwab's fabricated `0` from IBKR's genuine breakeven close
  without consulting the broker type, pushing broker knowledge into a service layer that has
  none today.
- **Subtract commission from IBKR values to recover gross.** Rejected: still leaves Schwab
  broken, still wrong for unprorated split children, and depends on an undocumented broker
  behaviour that could change.

### 2. Do not switch the closing-leg signal from `pnl` to `open_close`

The intuitive reading — *"`pnl` should mean P&L, so use `open_close='C'` to detect closing
legs"* — is semantically right but not currently implementable.

Migration `d7e2f1a9c4b8` added `open_close` with **no backfill**. Local distribution:

```
open_close | pnl        | origin   | count
-----------+------------+----------+------
NULL       | non-null≠0 | imported |  326
NULL       | non-null≠0 | split    |   63
C          | non-null≠0 | imported |   18
C          | 0 (Schwab) | imported |   10
```

389 legs carry real P&L but `open_close = NULL`. Rewiring `is_closing_leg` to `open_close`
would reclassify all of them as *opening* legs and rewrite FIFO matching. Further gaps, all
verified: `LogicalExecutionCreate`/`Update` (`schemas/execution.py:30-88`) have no
`open_close` field, so API-created legs are `NULL` and the field is not patchable;
`TradeService.create_trade` (`trade_service.py:405-458`) omits it on synthetic legs;
`ExecutionService.split_execution`/`merge_executions` do not propagate it while
`import_service.py:2024/2124/2152` does; IBKR mixed executions are `NULL` by design; no CHECK
constraint exists.

*Decision:* leave `is_closing_leg` on `pnl` and make that legitimate by specifying it as an
aggregator-internal signal. The spec records that no other component may read meaning from
the field. Making `open_close` authoritative is a prerequisite-heavy change (backfill, schema
plumbing, propagation fixes) that belongs on its own.

### 3. Do not touch the combo path in this change

Combos sum leg P&L in **both** paths (`aggregator.py:327-328`, `execution.py:1080-1083`), so
they are self-consistent — re-aggregation already reproduces import. They inherit the IBKR
net/gross conflation:

```
symbol | pnl        | net_pnl    | commission | Σ leg_pnl
-------+------------+------------+------------+-----------
DIA    | -147.18702 | -151.37405 |    4.18702 | -147.18702
QQQ    | -199.66063 | -204.32125 |    4.66063 | -199.66063
```

`pnl == Σ leg_pnl` (net), then commission is subtracted again.

*Rationale for excluding it:* combos have no meaningful multi-leg entry/exit prices, so the
price formula does not apply. The fix is a different one — `net_pnl = Σ leg.pnl` and
`pnl = Σ leg.pnl + commission` — which changes the meaning of stored values and requires
updating two tests that pin current behaviour (`test_execution_api.py:317`,
`test_execution_reaggregation.py:162`). Bundling it would mix a *divergence* fix with a
*semantics* fix and make the regression surface ambiguous.

### 4. Handle orphaned lots explicitly rather than relying on the broker value

The only case where price-derived P&L is impossible is an orphaned closing leg — the opening
execution predates the import window and `entry_price` is the `0.001` placeholder from
`aggregator.py:704`. Today the broker-P&L branch incidentally covers this.

There are **0 such trades in both databases**, so no behaviour regresses. Rather than keep an
incorrect branch for a population that does not exist, the spec requires the case be marked
as not-derivable. Note that `_re_aggregate_trade` already mishandles orphans independently:
with no entry-side execution, `entry_qty = 0` drives `entry_price` to `0` at `:1093`,
destroying the placeholder. That pre-existing gap is recorded, not fixed here.

### 5. Correct data through the service layer, not SQL

Re-run `re_aggregate_trade` on the two affected trades after the fix. For TGT the split leg's
unprorated `pnl` must be cleared first, otherwise re-aggregation reproduces the error — the
value lives on a 1-share leg and describes 20 shares.

*Rationale:* exercises the repaired path end to end and doubles as verification. Direct SQL
would bypass the logic under test.

## Risks / Trade-offs

- **Re-aggregating an IBKR trade now yields a different number than before.** → This is the
  point: the new number is the price-derived one that import already stored. Verified across
  259 trades that `Σ leg.pnl == net_pnl`, so the old branch was producing a net value labelled
  as gross. No stored value changes until a trade is re-aggregated.
- **Silent behaviour change for anyone relying on broker P&L appearing in `Trade.pnl`.** → No
  API or schema change; `LogicalExecution.pnl` keeps its values and remains queryable as
  provenance. The aggregator has behaved this way since April 2026, so this aligns
  re-aggregation with the long-standing import behaviour rather than introducing a new one.
- **Combo trades stay wrong (commission double-counted).** → Documented in the proposal as
  out of scope, with data. Self-consistent across both paths, so no new divergence is
  introduced by leaving it.
- **`pnl` remains dual-purpose (value + closing-leg marker).** → Constrained by spec to
  aggregator-internal use. The `open_close` migration path is described in Decision 2 for
  whoever picks it up.
- **Orphaned lots would lose their fallback.** → Zero rows in both databases; verify with
  `SELECT count(*) FROM trades WHERE entry_price = 0.001` before deploying.
- **Unprorated split children remain in the data** (`import_service.py:2015`). → After this
  change they no longer affect `Trade.pnl`. The stale leg values are still wrong as
  provenance; recorded as a follow-up.

## Migration Plan

No schema migration. Deployment is a code change only.

1. Confirm production is still clean using the deviation scan (§ Verification below). Expected: 0 rows.
2. Deploy the code change.
3. Re-aggregate the two local dev trades (DIOD, TGT) after clearing TGT's split-leg `pnl`.
4. Re-run the deviation scan on production. Expected: still 0 rows.

**Rollback:** revert the commit. No data is rewritten by the change itself, so no restore is
needed; any trade re-aggregated in the interim will have a corrected (price-derived) value
that remains valid under the old code as well, since the old code only diverges when broker
P&L is present.

**Verification query** — any row returned is a trade whose stored P&L disagrees with its prices:

```sql
WITH tb AS (
  SELECT t.id, t.symbol, t.direction, t.quantity, t.entry_price, t.exit_price,
         t.multiplier, t.pnl, max(brt.broker_type) AS broker
  FROM trades t
  JOIN logical_executions le ON le.trade_id = t.id
  JOIN broker_raw_transactions brt ON le.source_id = brt.id
  WHERE t.pnl IS NOT NULL AND t.exit_price IS NOT NULL AND t.is_combo = false
  GROUP BY t.id
)
SELECT broker, symbol, pnl,
       CASE WHEN direction='LONG' THEN (exit_price-entry_price)*quantity*multiplier
            ELSE (entry_price-exit_price)*quantity*multiplier END AS expected
FROM tb
WHERE abs(pnl - (CASE WHEN direction='LONG' THEN (exit_price-entry_price)*quantity*multiplier
                      ELSE (entry_price-exit_price)*quantity*multiplier END)) > 0.01;
```

## Open Questions

- Should `pnl-calculation` also constrain `pnl_eur`/`net_pnl_eur`? `aggregator.py:767` guards
  EUR conversion with `exec_trade_pnl != Decimal("0")`, which silently suppresses conversion
  for Schwab closes and for genuine IBKR breakeven closes. Irrelevant for USD accounts, not
  for EUR reporting. Left out of scope pending a decision on whether EUR values are derived
  or broker-sourced.
- Should the two split implementations be unified now or in the follow-up that addresses
  `open_close` propagation? Both diverge along the same seam
  (`import_service.py` vs `execution.py`).
