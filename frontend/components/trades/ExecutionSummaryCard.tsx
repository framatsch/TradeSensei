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
  const isMult = trade.multiplier > 1;

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
