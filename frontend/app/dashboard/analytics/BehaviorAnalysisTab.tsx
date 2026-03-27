"use client";

/**
 * BehaviorAnalysisTab — tag frequency chart + tag performance table.
 *
 * Section 1: Horizontal BarChart showing how often each tag appears.
 * Section 2: Table with per-tag performance stats (Win Rate, P&L, etc.).
 */

import { useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LabelList,
  Cell,
} from "recharts";
import { Tag as TagIcon } from "lucide-react";
import { Spinner } from "@/components/ui/Spinner";
import { CHART_COLORS } from "@/lib/constants";
import type { Trade, Tag } from "@/lib/types";

// ─── Helpers ──────────────────────────────────────────────────────────────────

const RED_HEX_PREFIXES = ["#f", "#e", "#d"]; // rose / red / pink shades

function isErrorTag(tag: Tag): boolean {
  const nameLower = tag.name.toLowerCase();
  if (
    nameLower.includes("mistake") ||
    nameLower.includes("error") ||
    nameLower.includes("fehler")
  )
    return true;
  if (tag.color) {
    const c = tag.color.toLowerCase();
    return RED_HEX_PREFIXES.some((p) => c.startsWith(p));
  }
  return false;
}

// ─── Tag aggregation ─────────────────────────────────────────────────────────

interface TagStats {
  id: string;
  name: string;
  color: string | null;
  isError: boolean;
  tradeCount: number;
  winRate: number;
  totalPnl: number;
  avgPnl: number;
  profitFactor: number;
}

function aggregateByTag(trades: Trade[]): TagStats[] {
  const map = new Map<
    string,
    {
      tag: Tag;
      trades: number;
      wins: number;
      totalPnl: number;
      grossProfit: number;
      grossLoss: number;
    }
  >();

  for (const trade of trades) {
    if (!trade.tags || trade.tags.length === 0) continue;
    const pnl =
      trade.pnl !== null ? parseFloat(trade.pnl) : null;

    for (const tag of trade.tags) {
      if (!map.has(tag.id)) {
        map.set(tag.id, {
          tag,
          trades: 0,
          wins: 0,
          totalPnl: 0,
          grossProfit: 0,
          grossLoss: 0,
        });
      }
      const entry = map.get(tag.id)!;
      entry.trades++;
      if (pnl !== null) {
        entry.totalPnl += pnl;
        if (pnl > 0) { entry.wins++; entry.grossProfit += pnl; }
        else if (pnl < 0) { entry.grossLoss += Math.abs(pnl); }
      }
    }
  }

  const stats: TagStats[] = [];
  map.forEach((entry) => {
    const { tag, trades: count, wins, totalPnl, grossProfit, grossLoss } =
      entry;
    const winRate = count > 0 ? (wins / count) * 100 : 0;
    const avgPnl = count > 0 ? totalPnl / count : 0;
    const profitFactor =
      grossLoss > 0 ? grossProfit / grossLoss : grossProfit > 0 ? 99 : 0;

    stats.push({
      id: tag.id,
      name: tag.name,
      color: tag.color,
      isError: isErrorTag(tag),
      tradeCount: count,
      winRate,
      totalPnl,
      avgPnl,
      profitFactor,
    });
  });

  // Sort by trade count descending
  stats.sort((a, b) => b.tradeCount - a.tradeCount);
  return stats;
}

// ─── Formatting ───────────────────────────────────────────────────────────────

const currencyFmt = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 2,
});

function pnlClass(val: number): string {
  if (val > 0) return "text-emerald-500";
  if (val < 0) return "text-rose-500";
  return "text-muted-foreground";
}

// ─── Props ────────────────────────────────────────────────────────────────────

interface BehaviorAnalysisTabProps {
  trades: Trade[];
  isLoading: boolean;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function BehaviorAnalysisTab({
  trades,
  isLoading,
}: BehaviorAnalysisTabProps) {
  const tagStats = useMemo(() => aggregateByTag(trades), [trades]);

  // Data for horizontal bar chart
  const chartData = useMemo(
    () =>
      tagStats.map((t) => ({
        name: t.name,
        count: t.tradeCount,
        isError: t.isError,
        color: t.color,
      })),
    [tagStats]
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Spinner size="lg" />
      </div>
    );
  }

  if (tagStats.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-lg border border-border bg-card py-24 gap-4">
        <TagIcon className="w-10 h-10 text-muted-foreground/40" />
        <p className="text-muted-foreground text-sm">
          No tags found. Tag your trades to see behavior patterns.
        </p>
      </div>
    );
  }

  // Dynamic height for the horizontal chart (min 200px, 40px per tag)
  const chartHeight = Math.max(200, tagStats.length * 40);

  return (
    <div className="flex flex-col gap-8">
      {/* ── Section 1: Tag Frequency ─────────────────────────────────────── */}
      <section>
        <div className="mb-4 flex items-center gap-2">
          <TagIcon className="w-4 h-4 text-muted-foreground" />
          <h2 className="text-sm font-semibold text-foreground">
            Tag Frequency
          </h2>
          <span className="text-xs text-muted-foreground">
            — how often each tag appears across trades
          </span>
        </div>

        <div
          className="rounded-lg border border-border bg-card p-4"
          style={{ height: chartHeight + 48 }}
        >
          <ResponsiveContainer width="100%" height={chartHeight}>
            <BarChart
              layout="vertical"
              data={chartData}
              margin={{ top: 4, right: 48, left: 8, bottom: 4 }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                horizontal={false}
                stroke={CHART_COLORS.grid}
              />
              <XAxis
                type="number"
                allowDecimals={false}
                tick={{ fill: CHART_COLORS.tick, fontSize: 11 }}
                axisLine={{ stroke: CHART_COLORS.axis }}
                tickLine={false}
              />
              <YAxis
                type="category"
                dataKey="name"
                width={130}
                tick={{ fill: CHART_COLORS.tick, fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                cursor={{ fill: "rgba(255,255,255,0.04)" }}
                contentStyle={{
                  background: CHART_COLORS.tooltip.bg,
                  border: `1px solid ${CHART_COLORS.tooltip.border}`,
                  borderRadius: "8px",
                }}
                labelStyle={{ color: CHART_COLORS.tooltip.text }}
                itemStyle={{ color: CHART_COLORS.tooltip.text }}
                formatter={(value: unknown) => [value as number, "Trades"]}
              />
              <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                <LabelList
                  dataKey="count"
                  position="right"
                  style={{ fill: CHART_COLORS.tick, fontSize: 11 }}
                />
                {chartData.map((entry, index) => (
                  <Cell
                    key={`tag-bar-${index}`}
                    fill={
                      entry.isError
                        ? CHART_COLORS.danger
                        : entry.color ?? CHART_COLORS.primary
                    }
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      {/* ── Section 2: Tag Performance Table ─────────────────────────────── */}
      <section>
        <div className="mb-4 flex items-center gap-2">
          <TagIcon className="w-4 h-4 text-muted-foreground" />
          <h2 className="text-sm font-semibold text-foreground">
            Tag Performance
          </h2>
        </div>

        <div className="rounded-lg border border-border bg-card overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-muted/50">
                <th className="px-4 py-3 text-left text-[10px] font-bold uppercase tracking-widest text-muted-foreground whitespace-nowrap">
                  Tag
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
                  Avg P&amp;L
                </th>
                <th className="px-4 py-3 text-right text-[10px] font-bold uppercase tracking-widest text-muted-foreground whitespace-nowrap">
                  Profit Factor
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {tagStats.map((row, idx) => (
                <tr
                  key={row.id}
                  className={[
                    idx % 2 === 1 ? "bg-muted/20" : "",
                    "hover:bg-muted/30 transition-colors",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                >
                  <td className="px-4 py-3 whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      {row.color && (
                        <span
                          className="inline-block w-2 h-2 rounded-full shrink-0"
                          style={{ backgroundColor: row.color }}
                        />
                      )}
                      <span
                        className={
                          row.isError
                            ? "text-rose-500 font-medium"
                            : "text-foreground"
                        }
                      >
                        {row.name}
                      </span>
                      {row.isError && (
                        <span className="text-[10px] font-bold uppercase tracking-widest rounded px-1 py-0.5 bg-rose-500/10 text-rose-500">
                          Error
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-foreground">
                    {row.tradeCount}
                  </td>
                  <td
                    className={[
                      "px-4 py-3 text-right font-mono",
                      row.winRate > 50
                        ? "text-emerald-500"
                        : row.winRate < 50
                        ? "text-rose-500"
                        : "text-muted-foreground",
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
                    {currencyFmt.format(row.totalPnl)}
                  </td>
                  <td
                    className={[
                      "px-4 py-3 text-right font-mono",
                      pnlClass(row.avgPnl),
                    ].join(" ")}
                  >
                    {currencyFmt.format(row.avgPnl)}
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-muted-foreground">
                    {row.profitFactor >= 99 ? "∞" : row.profitFactor.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
