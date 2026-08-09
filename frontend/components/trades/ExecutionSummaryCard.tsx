/*
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

/**
 * ExecutionSummaryCard — shows VWAP-computed trade summary from execution legs.
 */

"use client";

import { useMemo } from "react";
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

function formatContractLabel(symbol: string, type: string | null, strike: string | null, expiry: string | null): string | null {
  if (type && strike && expiry) {
    const typeLabel = type === "C" ? "Call" : type === "P" ? "Put" : "";
    const formattedStrike = parseFloat(strike).toString();
    const d = new Date(expiry + "T12:00:00Z");
    const formattedExpiry = d.toLocaleString("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" });
    return `${symbol} ${formattedStrike} ${typeLabel} · ${formattedExpiry}`;
  }
  return null;
}

/**
 * Compact per-leg contract label for the COMBO instrument column
 * (e.g. "620 Call"). Deliberately omits the underlying symbol (already shown
 * in the trade detail page header) and the expiry date (already a sortable
 * column in the execution legs table below) to avoid repeating the same
 * text on every row of a multi-leg strategy.
 */
function formatCompactContractLabel(type: string | null, strike: string | null): string | null {
  if (type && strike) {
    const typeLabel = type === "C" ? "Call" : type === "P" ? "Put" : "";
    const formattedStrike = parseFloat(strike).toString();
    return `${formattedStrike} ${typeLabel}`;
  }
  return null;
}

export function ExecutionSummaryCard({ trade, executions }: Props) {
  const count = executions.length;
  const activeExecutions = useMemo(() => executions.filter((execution) => !execution.deleted), [executions]);
  const isMult = trade.multiplier > 1;

  if (trade.is_combo) {
    const { rows, totalCommission, totalPnl, hasBrokerPnl } = useMemo(() => {
      const grouped = new Map<
        string,
        {
          symbol: string;
          assetClass: string;
          conid: string | null;
          optionType: string | null;
          strike: string | null;
          expiry: string | null;
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
        const key = `${execution.symbol}:${execution.asset_class}:${execution.option_type ?? "none"}:${execution.strike ?? "none"}:${execution.expiry ?? "none"}:${execution.conid ?? "none"}`;
        const qty = parseFloat(execution.raw_quantity);
        const price = parseFloat(execution.raw_price);
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
            conid: execution.conid,
            optionType: execution.option_type ?? null,
            strike: execution.strike ?? null,
            expiry: execution.expiry ?? null,
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

      return { rows, totalCommission, totalPnl, hasBrokerPnl };
    }, [activeExecutions]);

    return (
      <div className="bg-card rounded-xl border border-border p-4">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-sm font-semibold text-foreground">Execution Summary</h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              COMBO breakdown from {activeExecutions.length} execution leg{activeExecutions.length !== 1 ? "s" : ""}
            </p>
            <p className="text-[11px] text-muted-foreground mt-1">
              Uses raw execution values (chart markers may show split-adjusted prices).
            </p>
          </div>
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-muted text-muted-foreground border border-border uppercase tracking-wider">
            Computed
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-[color-mix(in_srgb,var(--muted)_40%,transparent)]">
                <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">Direction</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">Instrument</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-muted-foreground">Quantity</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-muted-foreground">Price</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-muted-foreground">Notional</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const label = formatCompactContractLabel(row.optionType, row.strike);
                return (
                  <tr key={`${row.symbol}-${row.assetClass}-${row.optionType ?? "none"}-${row.strike ?? "none"}-${row.expiry ?? "none"}-${row.conid ?? "none"}`} className="border-b border-[color-mix(in_srgb,var(--border)_60%,transparent)] last:border-b-0">
                    <td className="px-3 py-2">
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase bg-muted text-foreground border border-border">
                        {row.direction}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-foreground">
                      {label ? label : (
                        <>
                          {row.symbol} {row.assetClass}
                          {row.conid && <span className="ml-1 text-xs text-muted-foreground">({row.conid})</span>}
                        </>
                      )}
                    </td>
                    <td className="px-3 py-2 text-right text-foreground font-mono">
                      {fmtQty(row.quantity)} <span className="font-sans">{row.multiplier > 1 ? "contracts" : "shares"}</span>
                      {row.multiplier > 1 && (
                        <span className="ml-2 text-xs text-muted-foreground font-sans">&times;{row.multiplier}</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-right text-foreground font-mono">
                      {row.vwap === null ? "—" : fmt(row.vwap)}
                    </td>
                    <td className="px-3 py-2 text-right text-foreground font-mono">
                      {row.notional === null ? "—" : fmt(row.notional)}
                    </td>
                  </tr>
                );
              })}
              <tr className="bg-[color-mix(in_srgb,var(--muted)_30%,transparent)]">
                <td className="px-3 py-2 text-xs font-medium text-muted-foreground" colSpan={3}>
                  Total Commission: <span className="text-foreground font-mono">{fmt(totalCommission)}</span>
                </td>
                <td className="px-3 py-2 text-xs font-medium text-muted-foreground" colSpan={2}>
                  Combined P&amp;L:{" "}
                  <span className="text-foreground font-mono">{hasBrokerPnl ? fmt(totalPnl) : "—"}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  const headerQuantity = trade.chart_quantity ?? trade.quantity;
  const headerEntryPrice = trade.chart_entry_price ?? trade.entry_price;
  const headerExitPrice = trade.chart_exit_price ?? trade.exit_price;

  const notionalEntry =
    isMult && headerEntryPrice !== null && headerQuantity !== null
      ? parseFloat(headerEntryPrice) * parseFloat(headerQuantity) * trade.multiplier
      : null;

  const notionalExit =
    isMult && headerExitPrice !== null && headerQuantity !== null
      ? parseFloat(headerExitPrice) * parseFloat(headerQuantity) * trade.multiplier
      : null;

  const optionLeg = executions.find((ex) => ex.option_type !== null);
  const contractLabel = optionLeg ? formatContractLabel(optionLeg.symbol, optionLeg.option_type ?? null, optionLeg.strike ?? null, optionLeg.expiry ?? null) : null;

  return (
    <div className="bg-card rounded-xl border border-border p-4">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-sm font-semibold text-foreground">Execution Summary</h3>
          {contractLabel && (
            <p className="text-sm font-medium text-foreground mt-1">{contractLabel}</p>
          )}
          <p className="text-xs text-muted-foreground mt-0.5">
            Values are computed from {count} execution leg{count !== 1 ? "s" : ""}
          </p>
          <p className="text-[11px] text-muted-foreground mt-1">
            Uses chart-adjusted trade header values when available; execution rows may still show raw values.
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
            <dd className="font-medium text-foreground text-sm font-mono">{trade.multiplier}&times;</dd>
          </div>
        )}
        <div>
          <dt className="text-xs text-muted-foreground mb-0.5">
            {isMult ? "Entry Price (per unit)" : "VWAP Entry"}
          </dt>
          <dd className="font-medium text-foreground text-sm font-mono">{fmt(headerEntryPrice)}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground mb-0.5">
            {isMult ? "Exit Price (per unit)" : "VWAP Exit"}
          </dt>
          <dd className="font-medium text-foreground text-sm font-mono">{fmt(headerExitPrice)}</dd>
        </div>
        {isMult && notionalEntry !== null && (
          <div>
            <dt className="text-xs text-muted-foreground mb-0.5">Notional Entry</dt>
            <dd className="font-medium text-foreground text-sm font-mono">{fmt(notionalEntry)}</dd>
          </div>
        )}
        {isMult && notionalExit !== null && (
          <div>
            <dt className="text-xs text-muted-foreground mb-0.5">Notional Exit</dt>
            <dd className="font-medium text-foreground text-sm font-mono">{fmt(notionalExit)}</dd>
          </div>
        )}
        <div>
          <dt className="text-xs text-muted-foreground mb-0.5">Total Quantity</dt>
          <dd className="font-medium text-foreground text-sm font-mono">{fmtQty(headerQuantity)}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground mb-0.5">Total Commission</dt>
          <dd className="font-medium text-foreground text-sm font-mono">{fmt(trade.commission)}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground mb-0.5">P&amp;L</dt>
          <dd className="font-medium text-foreground text-sm font-mono">
            {trade.pnl ? (
              <span className={parseFloat(trade.pnl) >= 0 ? "text-success" : "text-danger"}>
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
          <dd className="font-medium text-foreground text-sm font-mono">{fmt(trade.stop_loss)}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground mb-0.5">Take Profit</dt>
          <dd className="font-medium text-foreground text-sm font-mono">{fmt(trade.take_profit)}</dd>
        </div>
      </div>
    </div>
  );
}
