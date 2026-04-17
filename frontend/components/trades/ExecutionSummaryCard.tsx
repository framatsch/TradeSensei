/**
 * ExecutionSummaryCard — shows VWAP-computed trade summary from execution legs.
 */

"use client";

import type { LogicalExecution, Trade } from "@/lib/types";

interface Props {
  trade: Trade;
  executions: LogicalExecution[];
}

function fmt(value: string | number | null, prefix = "$"): string {
  if (value === null || value === undefined) return "—";
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "—";
  return `${prefix}${num.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  })}`;
}

function fmtQty(value: string | number | null): string {
  if (value === null || value === undefined) return "—";
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "—";
  return num.toLocaleString("en-US", { maximumFractionDigits: 4 });
}

export function ExecutionSummaryCard({ trade, executions }: Props) {
  const count = executions.length;
  const activeExecutions = executions.filter((execution) => !execution.deleted);
  const isMult = trade.multiplier > 1;

  if (trade.is_combo) {
    const grouped = new Map<
      string,
      {
        symbol: string;
        assetClass: string;
        multiplier: number;
        direction: "LONG" | "SHORT";
        firstSeenAt: number;
        quantity: number;
        vwap: number | null;
        notional: number | null;
      }
    >();
    const groupCost = new Map<string, number>();

    let totalCommission = 0;
    let totalPnl = 0;
    let hasBrokerPnl = false;

    for (const execution of activeExecutions) {
      const key = `${execution.symbol}:${execution.asset_class}`;
      const qty = parseFloat(execution.quantity);
      const price = parseFloat(execution.price);
      const multiplier = execution.multiplier;
      const commission = parseFloat(execution.commission);
      const pnl = execution.pnl === null ? null : parseFloat(execution.pnl);

      if (!isNaN(commission)) {
        totalCommission += commission;
      }
      if (pnl !== null && !isNaN(pnl)) {
        hasBrokerPnl = true;
        totalPnl += pnl;
      }

      const existing = grouped.get(key);

      if (!existing) {
        const initialQty = !isNaN(qty) ? qty : 0;
        const initialCost = !isNaN(qty) && !isNaN(price) ? qty * price : 0;
        const firstSeenAt = new Date(execution.executed_at).getTime();
        grouped.set(key, {
          symbol: execution.symbol,
          assetClass: execution.asset_class,
          multiplier,
          direction: execution.direction,
          firstSeenAt,
          quantity: initialQty,
          vwap: initialQty > 0 ? initialCost / initialQty : null,
          notional:
            initialQty > 0 && initialCost >= 0
              ? (initialCost / initialQty) * initialQty * multiplier
              : null,
        });
        groupCost.set(key, initialCost);
        continue;
      }

      if (execution.direction === existing.direction && !isNaN(qty) && !isNaN(price)) {
        const prevQty = existing.quantity;
        const prevCost = groupCost.get(key) ?? (existing.vwap ?? 0) * prevQty;
        const nextQty = prevQty + qty;
        const nextCost = prevCost + qty * price;
        existing.quantity = nextQty;
        existing.vwap = nextQty > 0 ? nextCost / nextQty : null;
        existing.notional = existing.vwap !== null ? existing.vwap * nextQty * existing.multiplier : null;
        groupCost.set(key, nextCost);
      }
    }

    const rows = Array.from(grouped.values()).sort(
      (a, b) => a.firstSeenAt - b.firstSeenAt,
    );

    return (
      <div className="bg-card rounded-xl border border-border p-4">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-sm font-semibold text-foreground">Execution Summary</h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              COMBO breakdown from {activeExecutions.length} execution leg{activeExecutions.length !== 1 ? "s" : ""}
            </p>
          </div>
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-muted text-muted-foreground border border-border uppercase tracking-wider">
            Computed
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/40">
                <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">Direction</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">Instrument</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-muted-foreground">Quantity</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-muted-foreground">Price</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-muted-foreground">Notional</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={`${row.symbol}-${row.assetClass}`} className="border-b border-border/60 last:border-b-0">
                  <td className="px-3 py-2">
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase bg-muted text-foreground border border-border">
                      {row.direction}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-foreground">
                    {row.symbol} {row.assetClass}
                  </td>
                  <td className="px-3 py-2 text-right text-foreground">
                    {fmtQty(row.quantity)} {row.multiplier > 1 ? "contracts" : "shares"}
                    {row.multiplier > 1 && (
                      <span className="ml-2 text-xs text-muted-foreground">&times;{row.multiplier}</span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-right text-foreground">
                    {row.vwap === null ? "—" : fmt(row.vwap)}
                  </td>
                  <td className="px-3 py-2 text-right text-foreground">
                    {row.notional === null ? "—" : fmt(row.notional)}
                  </td>
                </tr>
              ))}
              <tr className="bg-muted/30">
                <td className="px-3 py-2 text-xs font-medium text-muted-foreground" colSpan={3}>
                  Total Commission: <span className="text-foreground">{fmt(totalCommission)}</span>
                </td>
                <td className="px-3 py-2 text-xs font-medium text-muted-foreground" colSpan={2}>
                  Combined P&amp;L:{" "}
                  <span className="text-foreground">{hasBrokerPnl ? fmt(totalPnl) : "—"}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  const notionalEntry =
    isMult && trade.entry_price !== null && trade.quantity !== null
      ? parseFloat(trade.entry_price) * parseFloat(trade.quantity) * trade.multiplier
      : null;

  const notionalExit =
    isMult && trade.exit_price !== null && trade.quantity !== null
      ? parseFloat(trade.exit_price) * parseFloat(trade.quantity) * trade.multiplier
      : null;

  return (
    <div className="bg-card rounded-xl border border-border p-4">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-sm font-semibold text-foreground">Execution Summary</h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Values are computed from {count} execution leg{count !== 1 ? "s" : ""}
          </p>
        </div>
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-muted text-muted-foreground border border-border uppercase tracking-wider">
          Computed
        </span>
      </div>

      <div className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-3">
        {isMult && (
          <div>
            <dt className="text-xs text-muted-foreground mb-0.5">Multiplier</dt>
            <dd className="font-medium text-foreground text-sm">{trade.multiplier}&times;</dd>
          </div>
        )}
        <div>
          <dt className="text-xs text-muted-foreground mb-0.5">
            {isMult ? "Entry Price (per unit)" : "VWAP Entry"}
          </dt>
          <dd className="font-medium text-foreground text-sm">{fmt(trade.entry_price)}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground mb-0.5">
            {isMult ? "Exit Price (per unit)" : "VWAP Exit"}
          </dt>
          <dd className="font-medium text-foreground text-sm">{fmt(trade.exit_price)}</dd>
        </div>
        {isMult && notionalEntry !== null && (
          <div>
            <dt className="text-xs text-muted-foreground mb-0.5">Notional Entry</dt>
            <dd className="font-medium text-foreground text-sm">{fmt(notionalEntry)}</dd>
          </div>
        )}
        {isMult && notionalExit !== null && (
          <div>
            <dt className="text-xs text-muted-foreground mb-0.5">Notional Exit</dt>
            <dd className="font-medium text-foreground text-sm">{fmt(notionalExit)}</dd>
          </div>
        )}
        <div>
          <dt className="text-xs text-muted-foreground mb-0.5">Total Quantity</dt>
          <dd className="font-medium text-foreground text-sm">{fmtQty(trade.quantity)}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground mb-0.5">Total Commission</dt>
          <dd className="font-medium text-foreground text-sm">{fmt(trade.commission)}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground mb-0.5">P&amp;L</dt>
          <dd className="font-medium text-foreground text-sm">
            {trade.pnl ? (
              <span className={parseFloat(trade.pnl) >= 0 ? "text-emerald-500" : "text-red-500"}>
                {parseFloat(trade.pnl) >= 0 ? "+" : ""}
                {fmt(trade.pnl)}
              </span>
            ) : (
              "—"
            )}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground mb-0.5">Stop Loss</dt>
          <dd className="font-medium text-foreground text-sm">{fmt(trade.stop_loss)}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground mb-0.5">Take Profit</dt>
          <dd className="font-medium text-foreground text-sm">{fmt(trade.take_profit)}</dd>
        </div>
      </div>
    </div>
  );
}
