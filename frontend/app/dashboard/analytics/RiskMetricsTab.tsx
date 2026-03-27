"use client";

/**
 * RiskMetricsTab — R-Multiple distribution histogram + drawdown statistics.
 *
 * Section 1: Recharts BarChart bucketing all closed trades by R-Multiple.
 * Section 2: Drawdown stat cards computed directly from the trades array.
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
  Cell,
  LabelList,
} from "recharts";
import { TrendingDown, Activity } from "lucide-react";
import {
  computeRMultiple,
  validateTradeForRMultiple,
  buildSufficiencyReport,
} from "@/lib/dataValidation";
import { InsufficientDataBanner } from "@/components/ui/InsufficientDataBanner";
import { Spinner } from "@/components/ui/Spinner";
import { CHART_COLORS } from "@/lib/constants";
import type { Trade } from "@/lib/types";

// ─── Bucket definitions ───────────────────────────────────────────────────────

interface RBucket {
  label: string;
  min: number;
  max: number;
  count: number;
}

const BUCKET_DEFS: Array<{ label: string; min: number; max: number }> = [
  { label: "< -3R", min: -Infinity, max: -3 },
  { label: "-3 to -2R", min: -3, max: -2 },
  { label: "-2 to -1R", min: -2, max: -1 },
  { label: "-1 to 0R", min: -1, max: 0 },
  { label: "0 to 1R", min: 0, max: 1 },
  { label: "1 to 2R", min: 1, max: 2 },
  { label: "2 to 3R", min: 2, max: 3 },
  { label: "> 3R", min: 3, max: Infinity },
];

function bucketColor(bucket: { min: number; max: number }): string {
  if (bucket.max <= 0) return CHART_COLORS.danger;
  if (bucket.min >= 1) return CHART_COLORS.success;
  return CHART_COLORS.warning; // 0-1 bucket
}

// ─── Drawdown helpers ─────────────────────────────────────────────────────────

interface DrawdownStats {
  maxDrawdownAbs: number;
  maxDrawdownPct: number;
  avgDrawdownPct: number;
  avgRecoveryTrades: number;
  currentStreakCount: number;
  currentStreakType: "winning" | "losing" | "none";
}

function computeDrawdownStats(trades: Trade[]): DrawdownStats {
  const closed = trades
    .filter((t) => t.closed_at !== null && t.pnl !== null)
    .sort(
      (a, b) =>
        new Date(a.closed_at!).getTime() - new Date(b.closed_at!).getTime()
    );

  if (closed.length === 0) {
    return {
      maxDrawdownAbs: 0,
      maxDrawdownPct: 0,
      avgDrawdownPct: 0,
      avgRecoveryTrades: 0,
      currentStreakCount: 0,
      currentStreakType: "none",
    };
  }

  // Build cumulative P&L series
  const pnls = closed.map((t) => parseFloat(t.pnl!));
  const cumulative: number[] = [];
  let running = 0;
  for (const p of pnls) {
    running += p;
    cumulative.push(running);
  }

  // Peak → trough drawdown
  let peak = cumulative[0];
  let maxDrawdownAbs = 0;
  let maxDrawdownPct = 0;
  let drawdownDepths: number[] = [];
  let inDrawdown = false;
  let recoveryLengths: number[] = [];
  let ddStart = 0;

  for (let i = 0; i < cumulative.length; i++) {
    if (cumulative[i] > peak) {
      if (inDrawdown) {
        recoveryLengths.push(i - ddStart);
        inDrawdown = false;
      }
      peak = cumulative[i];
    } else {
      const ddAbs = peak - cumulative[i];
      const ddPct = peak !== 0 ? (ddAbs / Math.abs(peak)) * 100 : 0;
      if (ddAbs > 0) {
        if (!inDrawdown) { ddStart = i; inDrawdown = true; }
        drawdownDepths.push(ddPct);
        if (ddAbs > maxDrawdownAbs) {
          maxDrawdownAbs = ddAbs;
          maxDrawdownPct = ddPct;
        }
      }
    }
  }

  const avgDrawdownPct =
    drawdownDepths.length > 0
      ? drawdownDepths.reduce((a, b) => a + b, 0) / drawdownDepths.length
      : 0;

  const avgRecoveryTrades =
    recoveryLengths.length > 0
      ? recoveryLengths.reduce((a, b) => a + b, 0) / recoveryLengths.length
      : 0;

  // Current streak from most recent trade backwards
  let currentStreakCount = 0;
  let currentStreakType: "winning" | "losing" | "none" = "none";

  for (let i = pnls.length - 1; i >= 0; i--) {
    const isWin = pnls[i] > 0;
    if (currentStreakType === "none") {
      currentStreakType = isWin ? "winning" : "losing";
      currentStreakCount = 1;
    } else if (
      (currentStreakType === "winning" && isWin) ||
      (currentStreakType === "losing" && !isWin)
    ) {
      currentStreakCount++;
    } else {
      break;
    }
  }

  return {
    maxDrawdownAbs,
    maxDrawdownPct,
    avgDrawdownPct,
    avgRecoveryTrades,
    currentStreakCount,
    currentStreakType,
  };
}

// ─── Stat card ────────────────────────────────────────────────────────────────

interface StatCardProps {
  label: string;
  value: string;
  subtext?: string;
  valueClass?: string;
}

function StatCard({ label, value, subtext, valueClass }: StatCardProps) {
  return (
    <div className="rounded-lg border border-border bg-card p-4 flex flex-col gap-1">
      <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
        {label}
      </span>
      <span className={`text-2xl font-bold font-mono ${valueClass ?? "text-foreground"}`}>
        {value}
      </span>
      {subtext && (
        <span className="text-xs text-muted-foreground">{subtext}</span>
      )}
    </div>
  );
}

// ─── Props ────────────────────────────────────────────────────────────────────

interface RiskMetricsTabProps {
  trades: Trade[];
  isLoading: boolean;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function RiskMetricsTab({ trades, isLoading }: RiskMetricsTabProps) {
  const closedTrades = useMemo(
    () => trades.filter((t) => t.closed_at !== null && t.pnl !== null),
    [trades]
  );

  // R-Multiple buckets
  const { buckets, sufficiencyReport } = useMemo(() => {
    const report = buildSufficiencyReport(closedTrades, validateTradeForRMultiple);

    const counts: number[] = BUCKET_DEFS.map(() => 0);
    for (const t of closedTrades) {
      const r = computeRMultiple(t);
      if (r === null) continue;
      for (let i = 0; i < BUCKET_DEFS.length; i++) {
        const b = BUCKET_DEFS[i];
        if (r >= b.min && r < b.max) {
          counts[i]++;
          break;
        }
      }
    }

    const result: RBucket[] = BUCKET_DEFS.map((b, i) => ({
      ...b,
      count: counts[i],
    }));

    return { buckets: result, sufficiencyReport: report };
  }, [closedTrades]);

  // Drawdown stats
  const dd = useMemo(() => computeDrawdownStats(trades), [trades]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Spinner size="lg" />
      </div>
    );
  }

  const fmt = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  });

  return (
    <div className="flex flex-col gap-8">
      {/* ── Section 1: R-Multiple Distribution ───────────────────────────── */}
      <section>
        <div className="mb-4 flex items-center gap-2">
          <Activity className="w-4 h-4 text-muted-foreground" />
          <h2 className="text-sm font-semibold text-foreground">
            R-Multiple Distribution
          </h2>
        </div>

        <InsufficientDataBanner
          report={sufficiencyReport}
          analysisName="R-Multiple Distribution"
          affectedTradesHref="/dashboard/trades"
          hidden={sufficiencyReport.coveragePercent === 100}
        />

        {closedTrades.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-lg border border-border bg-card py-16 gap-3">
            <Activity className="w-8 h-8 text-muted-foreground/40" />
            <p className="text-muted-foreground text-sm">
              No closed trades available for R-Multiple analysis.
            </p>
          </div>
        ) : (
          <div className="rounded-lg border border-border bg-card p-4 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={buckets}
                margin={{ top: 20, right: 16, left: 0, bottom: 8 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  vertical={false}
                  stroke={CHART_COLORS.grid}
                />
                <XAxis
                  dataKey="label"
                  tick={{ fill: CHART_COLORS.tick, fontSize: 11 }}
                  axisLine={{ stroke: CHART_COLORS.axis }}
                  tickLine={false}
                />
                <YAxis
                  allowDecimals={false}
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
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  <LabelList
                    dataKey="count"
                    position="top"
                    style={{ fill: CHART_COLORS.tick, fontSize: 11 }}
                    formatter={(v: unknown) => {
                      const n = v as number;
                      return n === 0 ? "" : n;
                    }}
                  />
                  {buckets.map((b, i) => (
                    <Cell key={`r-cell-${i}`} fill={bucketColor(b)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </section>

      {/* ── Section 2: Drawdown Statistics ───────────────────────────────── */}
      <section>
        <div className="mb-4 flex items-center gap-2">
          <TrendingDown className="w-4 h-4 text-muted-foreground" />
          <h2 className="text-sm font-semibold text-foreground">
            Drawdown Statistics
          </h2>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
          <StatCard
            label="Max Drawdown ($)"
            value={fmt.format(dd.maxDrawdownAbs)}
            subtext="Peak to trough"
            valueClass="text-rose-500"
          />
          <StatCard
            label="Max Drawdown (%)"
            value={`${dd.maxDrawdownPct.toFixed(2)}%`}
            subtext="Relative to equity peak"
            valueClass="text-rose-500"
          />
          <StatCard
            label="Avg Drawdown (%)"
            value={`${dd.avgDrawdownPct.toFixed(2)}%`}
            subtext="Average dip depth"
            valueClass="text-amber-500"
          />
          <StatCard
            label="Avg Recovery"
            value={
              dd.avgRecoveryTrades > 0
                ? `${Math.round(dd.avgRecoveryTrades)} trades`
                : "—"
            }
            subtext="Trades to recover peak"
          />
          <StatCard
            label="Current Streak"
            value={
              dd.currentStreakType === "none"
                ? "—"
                : `${dd.currentStreakCount} ${dd.currentStreakType === "winning" ? "W" : "L"}`
            }
            subtext={
              dd.currentStreakType === "none"
                ? "No trades yet"
                : dd.currentStreakType === "winning"
                ? "Consecutive wins"
                : "Consecutive losses"
            }
            valueClass={
              dd.currentStreakType === "winning"
                ? "text-emerald-500"
                : dd.currentStreakType === "losing"
                ? "text-rose-500"
                : "text-muted-foreground"
            }
          />
        </div>
      </section>
    </div>
  );
}
