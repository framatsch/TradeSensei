/**
 * DashboardHeader — Hero section of the dashboard.
 *
 * Displays the total net PnL prominently, win/loss breakdown, and a
 * subtle equity area chart that bleeds into the card background for the
 * "Radiant / Obsidian" deep-dark SaaS aesthetic.
 */

"use client";

import {
  AreaChart,
  Area,
  ResponsiveContainer,
  Tooltip,
  YAxis,
} from "recharts";
import type { MetricsSummary } from "@/lib/types";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatCurrency(value: string | number): string {
  const num = typeof value === "string" ? parseFloat(value) : value;
  const abs = Math.abs(num);
  const prefix = num >= 0 ? "+" : "−";
  if (abs >= 1_000_000) {
    return `${prefix}$${(abs / 1_000_000).toFixed(2)}M`;
  }
  if (abs >= 1_000) {
    return `${prefix}$${(abs / 1_000).toFixed(2)}K`;
  }
  return `${prefix}$${abs.toFixed(2)}`;
}

function formatPercent(value: string | null): string {
  if (!value) return "—";
  return `${(parseFloat(value) * 100).toFixed(1)}%`;
}

// ─── Mini Tooltip ─────────────────────────────────────────────────────────────

interface TooltipPayloadItem {
  value: number;
}

interface ChartTooltipProps {
  active?: boolean;
  payload?: TooltipPayloadItem[];
  label?: string;
}

function ChartTooltip({ active, payload }: ChartTooltipProps) {
  if (!active || !payload?.length) return null;
  const val = payload[0].value;
  const color = val >= 0 ? "#34d399" : "#fb7185";
  return (
    <div className="bg-popover border border-border rounded-lg px-3 py-2 shadow-2xl text-xs">
      <span style={{ color }} className="font-semibold tabular-nums">
        {formatCurrency(val)}
      </span>
    </div>
  );
}

// ─── Stat Pill ────────────────────────────────────────────────────────────────

interface StatPillProps {
  label: string;
  value: string;
  color?: string;
}

function StatPill({ label, value, color = "text-foreground" }: StatPillProps) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
        {label}
      </span>
      <span className={`text-sm font-semibold tabular-nums ${color}`}>
        {value}
      </span>
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

interface Props {
  summary: MetricsSummary;
}

export function DashboardHeader({ summary }: Props) {
  const { metrics, equity_curve, max_drawdown } = summary;
  const totalPnl = parseFloat(metrics.total_pnl);
  const isPositive = totalPnl >= 0;

  // Prepare chart data — equity values as numbers
  const chartData = equity_curve.map((p) => ({
    t: p.timestamp,
    v: parseFloat(p.equity),
  }));

  // Gradient colors based on overall performance
  const accentColor = isPositive ? "#34d399" : "#fb7185";
  const accentColorFaint = isPositive
    ? "rgba(52, 211, 153, 0.12)"
    : "rgba(251, 113, 133, 0.12)";

  return (
    <div className="radiant-card light-edge noise-overlay overflow-hidden">
      {/* Ambient radial glow in the top-right corner */}
      <div
        aria-hidden
        className="pointer-events-none absolute -top-24 -right-24 w-96 h-96 rounded-full opacity-20 blur-3xl"
        style={{
          background: `radial-gradient(circle, ${accentColor} 0%, transparent 70%)`,
        }}
      />

      <div className="relative z-10 flex flex-col lg:flex-row gap-6 p-6 lg:p-8">
        {/* Left — numbers */}
        <div className="flex flex-col gap-5 lg:min-w-[260px]">
          {/* Label */}
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
            Net P&amp;L · All Time
          </p>

          {/* Big number */}
          <div>
            <p
              className="text-5xl font-bold tracking-tight tabular-nums leading-none"
              style={{
                color: accentColor,
                filter: isPositive
                  ? "drop-shadow(0 0 8px rgba(52, 211, 153, 0.3))"
                  : "drop-shadow(0 0 8px rgba(251, 113, 133, 0.3))",
              }}
            >
              {formatCurrency(metrics.total_pnl)}
            </p>
            <p className="mt-2 text-sm text-muted-foreground tabular-nums">
              {metrics.total_trades} trades &mdash;{" "}
              {metrics.winning_trades}W / {metrics.losing_trades}L
            </p>
          </div>

          {/* Stat pills row */}
          <div className="flex items-center gap-6 pt-1 border-t border-border">
            <StatPill
              label="Win Rate"
              value={formatPercent(metrics.win_rate)}
              color={
                parseFloat(metrics.win_rate) >= 0.5
                  ? "text-success"
                  : "text-danger"
              }
            />
            <StatPill
              label="Profit Factor"
              value={
                metrics.profit_factor
                  ? parseFloat(metrics.profit_factor).toFixed(2)
                  : "—"
              }
              color={
                metrics.profit_factor &&
                parseFloat(metrics.profit_factor) >= 1
                  ? "text-success"
                  : "text-danger"
              }
            />
            <StatPill
              label="Max DD"
              value={
                max_drawdown
                  ? `${(parseFloat(max_drawdown) * 100).toFixed(1)}%`
                  : "—"
              }
              color="text-danger"
            />
          </div>
        </div>

        {/* Right — equity chart */}
        <div className="flex-1 min-h-[120px] lg:min-h-0 -mx-2">
          {chartData.length > 1 ? (
            <ResponsiveContainer width="100%" height="100%" minHeight={140}>
              <AreaChart
                data={chartData}
                margin={{ top: 8, right: 0, left: 0, bottom: 0 }}
              >
                <defs>
                  <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={accentColor} stopOpacity={0.25} />
                    <stop offset="100%" stopColor={accentColor} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <YAxis domain={["auto", "auto"]} hide />
                <Tooltip content={<ChartTooltip />} />
                <Area
                  type="monotone"
                  dataKey="v"
                  stroke={accentColor}
                  strokeWidth={2}
                  fill="url(#equityGrad)"
                  dot={false}
                  activeDot={{ r: 4, fill: accentColor, strokeWidth: 0 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div
              className="flex items-center justify-center h-full min-h-[140px] rounded-lg border border-dashed border-border"
              style={{ background: accentColorFaint }}
            >
              <p className="text-xs text-muted-foreground">
                No equity data yet
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
