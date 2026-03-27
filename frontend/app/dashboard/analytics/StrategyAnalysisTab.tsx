"use client";

/**
 * StrategyAnalysisTab — playbook performance summary table.
 *
 * Aggregates closed trades by playbook (or "No Playbook" bucket) and shows
 * Win Rate, Total P&L, Profit Factor, and Avg R-Multiple per strategy.
 * The best-performing playbook (by Total P&L) is highlighted.
 */

import { useMemo } from "react";
import { BarChart2 } from "lucide-react";
import { usePlaybooks } from "@/hooks/usePlaybooks";
import { computeRMultiple } from "@/lib/dataValidation";
import { Spinner } from "@/components/ui/Spinner";
import type { Trade } from "@/lib/types";

// ─── Types ────────────────────────────────────────────────────────────────────

interface PlaybookRow {
  id: string | null;
  name: string;
  trades: number;
  winRate: number;
  totalPnl: number;
  profitFactor: number;
  avgRMultiple: number | null;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

const fmt = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function formatPnl(val: number): string {
  return fmt.format(val);
}

function pnlClass(val: number): string {
  if (val > 0) return "text-emerald-500";
  if (val < 0) return "text-rose-500";
  return "text-muted-foreground";
}

// ─── Aggregation ─────────────────────────────────────────────────────────────

function aggregateByPlaybook(trades: Trade[]): PlaybookRow[] {
  // Only closed trades
  const closed = trades.filter((t) => t.closed_at !== null && t.pnl !== null);

  // Group by playbook_id (null = "No Playbook")
  const groups = new Map<string | null, Trade[]>();

  for (const t of closed) {
    const key = t.playbook_id ?? null;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(t);
  }

  const rows: PlaybookRow[] = [];

  groups.forEach((groupTrades, id) => {
    let wins = 0;
    let grossProfit = 0;
    let grossLoss = 0;
    let totalPnl = 0;
    let rSum = 0;
    let rCount = 0;

    for (const t of groupTrades) {
      const pnl = parseFloat(t.pnl ?? "0");
      totalPnl += pnl;
      if (pnl > 0) { grossProfit += pnl; wins++; }
      else if (pnl < 0) { grossLoss += Math.abs(pnl); }

      const r = computeRMultiple(t);
      if (r !== null) { rSum += r; rCount++; }
    }

    const count = groupTrades.length;
    const winRate = count > 0 ? (wins / count) * 100 : 0;
    const profitFactor =
      grossLoss > 0 ? grossProfit / grossLoss : grossProfit > 0 ? 99 : 0;
    const avgRMultiple = rCount > 0 ? rSum / rCount : null;

    const playbookName =
      id === null
        ? "No Playbook"
        : (groupTrades[0].playbook_name ?? `Playbook ${id.slice(0, 6)}`);

    rows.push({
      id,
      name: playbookName,
      trades: count,
      winRate,
      totalPnl,
      profitFactor,
      avgRMultiple,
    });
  });

  // Sort: best P&L first, "No Playbook" last
  rows.sort((a, b) => {
    if (a.id === null && b.id !== null) return 1;
    if (a.id !== null && b.id === null) return -1;
    return b.totalPnl - a.totalPnl;
  });

  return rows;
}

// ─── Props ────────────────────────────────────────────────────────────────────

interface StrategyAnalysisTabProps {
  trades: Trade[];
  isLoading: boolean;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function StrategyAnalysisTab({
  trades,
  isLoading,
}: StrategyAnalysisTabProps) {
  // Pre-fetch playbook list so we always have names even if playbook_name is stale
  const { data: playbooks } = usePlaybooks();
  const playbookNameMap = useMemo(() => {
    const m = new Map<string, string>();
    (playbooks ?? []).forEach((p) => m.set(p.id, p.name));
    return m;
  }, [playbooks]);

  const rows = useMemo(() => {
    const rawRows = aggregateByPlaybook(trades);
    // Enrich names from live playbook cache
    return rawRows.map((r) => ({
      ...r,
      name:
        r.id !== null
          ? (playbookNameMap.get(r.id) ?? r.name)
          : r.name,
    }));
  }, [trades, playbookNameMap]);

  // Best playbook = highest P&L among named playbooks
  const bestId = useMemo(() => {
    const named = rows.filter((r) => r.id !== null);
    if (named.length === 0) return null;
    return named.reduce((best, cur) =>
      cur.totalPnl > best.totalPnl ? cur : best
    ).id;
  }, [rows]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Spinner size="lg" />
      </div>
    );
  }

  if (rows.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-lg border border-border bg-card py-24 gap-4">
        <BarChart2 className="w-10 h-10 text-muted-foreground/40" />
        <p className="text-muted-foreground text-sm">
          No closed trades found. Record some trades to see strategy performance.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border bg-card overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-muted/50">
            <th className="px-4 py-3 text-left text-[10px] font-bold uppercase tracking-widest text-muted-foreground whitespace-nowrap">
              Playbook
            </th>
            <th className="px-4 py-3 text-right text-[10px] font-bold uppercase tracking-widest text-muted-foreground whitespace-nowrap">
              Trades
            </th>
            <th className="px-4 py-3 text-right text-[10px] font-bold uppercase tracking-widest text-muted-foreground whitespace-nowrap">
              Win Rate
            </th>
            <th className="px-4 py-3 text-right text-[10px] font-bold uppercase tracking-widest text-muted-foreground whitespace-nowrap">
              Total P&amp;L
            </th>
            <th className="px-4 py-3 text-right text-[10px] font-bold uppercase tracking-widest text-muted-foreground whitespace-nowrap">
              Profit Factor
            </th>
            <th className="px-4 py-3 text-right text-[10px] font-bold uppercase tracking-widest text-muted-foreground whitespace-nowrap">
              Avg R-Multiple
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {rows.map((row, idx) => {
            const isBest = row.id !== null && row.id === bestId;
            return (
              <tr
                key={row.id ?? "no-playbook"}
                className={[
                  idx % 2 === 1 ? "bg-muted/20" : "",
                  isBest
                    ? "bg-emerald-500/5 border-l-2 border-l-emerald-500"
                    : "",
                  "hover:bg-muted/30 transition-colors",
                ]
                  .filter(Boolean)
                  .join(" ")}
              >
                <td className="px-4 py-3 font-medium text-foreground whitespace-nowrap">
                  <div className="flex items-center gap-2">
                    {isBest && (
                      <span className="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-bold bg-emerald-500/15 text-emerald-500 uppercase tracking-widest">
                        Best
                      </span>
                    )}
                    <span className={row.id === null ? "text-muted-foreground italic" : ""}>
                      {row.name}
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3 text-right font-mono text-foreground">
                  {row.trades}
                </td>
                <td
                  className={[
                    "px-4 py-3 text-right font-mono",
                    row.winRate >= 50 ? "text-emerald-500" : "text-rose-500",
                  ].join(" ")}
                >
                  {row.winRate.toFixed(1)}%
                </td>
                <td
                  className={[
                    "px-4 py-3 text-right font-mono",
                    pnlClass(row.totalPnl),
                  ].join(" ")}
                >
                  {formatPnl(row.totalPnl)}
                </td>
                <td className="px-4 py-3 text-right font-mono text-muted-foreground">
                  {row.profitFactor >= 99
                    ? "∞"
                    : row.profitFactor.toFixed(2)}
                </td>
                <td className="px-4 py-3 text-right font-mono text-muted-foreground">
                  {row.avgRMultiple !== null
                    ? `${row.avgRMultiple >= 0 ? "+" : ""}${row.avgRMultiple.toFixed(2)}R`
                    : <span className="text-xs italic">N/A</span>}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
