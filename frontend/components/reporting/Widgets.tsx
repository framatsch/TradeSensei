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
 * Widget components for the Reporting Hub.
 *
 * Each widget handles its own loading and empty states and uses Recharts
 * for visualizations. Components follow the ChartShell wrapper pattern.
 */

"use client";

import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ZAxis,
} from "recharts";
import { ChartShell } from "@/components/charts/ChartShell";
import { MetricHelpLink } from "@/components/ui/MetricHelpLink";
import { EmptyState } from "./EmptyState";
import { ChartSkeleton } from "./ReportingSkeletons";

// ─── Shared helpers ────────────────────────────────────────────────────────────

function formatCurrency(value: string | number | null | undefined): string {
  if (value == null) return "—";
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(num);
}

function formatPercent(value: string | null | undefined): string {
  if (value == null) return "—";
  const num = parseFloat(value);
  if (isNaN(num)) return "—";
  return (num * 100).toFixed(1) + "%";
}

function formatNumber(value: number | null | undefined): string {
  if (value == null) return "—";
  return value.toLocaleString("en-US");
}

// ─── Types ─────────────────────────────────────────────────────────────────────

export interface EquityCurvePoint {
  date?: string;
  timestamp?: string; // keeping timestamp for fallback
  equity: number;
}

export interface DrawdownPoint {
  date?: string;
  timestamp?: string; // keeping timestamp for fallback
  drawdown: number;
}

export interface RMultipleBucket {
  bucket_min: string;
  bucket_max: string;
  count: number;
}

export interface ScatterPoint {
  x: number;
  y: number;
  count?: number;
  label?: string;
}

export interface HeatmapCell {
  playbook: string;
  phase: string;
  trade_count: number;
  win_rate: string;
  avg_pnl: string;
}

export interface AttributionBar {
  label: string;
  value: number;
  avg_pnl?: string;
  win_rate?: string;
}

export interface MetricCardData {
  label: string;
  value: string;
  sublabel?: string;
  trend?: "up" | "down" | "neutral";
  helpAnchor?: string;
}

// ─── Payoff Ratio ──────────────────────────────────────────────────────────────

export function PayoffRatio({
  avgWin,
  avgLoss,
}: {
  avgWin?: string | null;
  avgLoss?: string | null;
}) {
  const win = avgWin ? parseFloat(avgWin) : NaN;
  const loss = avgLoss ? Math.abs(parseFloat(avgLoss)) : NaN;
  const ratio = !isNaN(win) && !isNaN(loss) && loss !== 0 ? win / loss : null;

  return (
    <div className="bg-card rounded-xl border border-border p-5 flex flex-col justify-between">
      <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-2 flex items-center gap-1.5">
        Payoff Ratio
        <MetricHelpLink anchor="payoff-ratio" />
      </p>
      <p className="text-2xl font-semibold font-mono text-foreground">
        {ratio !== null ? ratio.toFixed(2) : "—"}
      </p>
      <p className="text-xs text-muted-foreground mt-1">
        {avgWin != null && avgLoss != null
          ? `Avg Win: ${formatCurrency(avgWin)} / Avg Loss: ${formatCurrency(avgLoss)}`
          : "No data"}
      </p>
    </div>
  );
}

// ─── Metric Card (reusable for key metrics) ────────────────────────────────────

export function MetricCard({ label, value, sublabel, trend, helpAnchor }: MetricCardData) {
  return (
    <div className="bg-card rounded-xl border border-border p-5 flex flex-col justify-between">
      <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-2 flex items-center gap-1.5">
        {label}
        {helpAnchor && <MetricHelpLink anchor={helpAnchor} />}
      </p>
      <p
        className={`text-2xl font-semibold font-mono ${
          trend === "up"
            ? "text-success"
            : trend === "down"
              ? "text-danger"
              : "text-foreground"
        }`}
      >
        {value}
      </p>
      {sublabel && (
        <p className="text-xs text-muted-foreground mt-1">{sublabel}</p>
      )}
    </div>
  );
}

// ─── Performance Classic: Equity Curve ─────────────────────────────────────────

export function EquityCurveWidget({
  data,
  isLoading,
}: {
  data?: EquityCurvePoint[];
  isLoading: boolean;
}) {
  if (isLoading) return <ChartSkeleton />;

  return (
    <ChartShell
      title="Equity Curve"
      isEmpty={!data || data.length === 0}
      emptyMessage="No equity curve data available."
      helpAnchor="equity-curve"
    >
      {data && data.length > 0 && (
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={data}>
            <defs>
              <linearGradient id="equityFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="var(--success)" stopOpacity={0.2} />
                <stop offset="95%" stopColor="var(--success)" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey={(d: any) => d.date || d.timestamp || ""}
              tick={{ fontSize: 11 }}
              tickFormatter={(d: string) =>
                d ? new Date(d).toLocaleDateString("en-US", {
                  month: "short",
                  year: "2-digit",
                }) : ""
              }
            />
            <YAxis
              tick={{ fontSize: 11 }}
              tickFormatter={(v: number) =>
                new Intl.NumberFormat("en-US", {
                  notation: "compact",
                  compactDisplay: "short",
                }).format(v)
              }
            />
            <Tooltip />
            <Area
              type="monotone"
              dataKey="equity"
              stroke="var(--success)"
              fill="url(#equityFill)"
              strokeWidth={2}
              name="Equity"
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </ChartShell>
  );
}

// ─── Performance Classic: Drawdown Curve ───────────────────────────────────────

export function DrawdownWidget({
  data,
  isLoading,
}: {
  data?: DrawdownPoint[];
  isLoading: boolean;
}) {
  if (isLoading) return <ChartSkeleton />;

  return (
    <ChartShell
      title="Drawdown"
      isEmpty={!data || data.length === 0}
      emptyMessage="No drawdown data available."
      helpAnchor="max-drawdown"
    >
      {data && data.length > 0 && (
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={data}>
            <defs>
              <linearGradient id="drawdownFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="var(--danger)" stopOpacity={0.2} />
                <stop offset="95%" stopColor="var(--danger)" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey={(d: any) => d.date || d.timestamp || ""}
              tick={{ fontSize: 11 }}
              tickFormatter={(d: string) =>
                d ? new Date(d).toLocaleDateString("en-US", {
                  month: "short",
                  year: "2-digit",
                }) : ""
              }
            />
            <YAxis
              tick={{ fontSize: 11 }}
              tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
            />
            <Tooltip
              formatter={(value) => [
                `${((value as number) * 100).toFixed(2)}%`,
                "Drawdown",
              ]}
            />
            <Area
              type="monotone"
              dataKey="drawdown"
              stroke="var(--danger)"
              fill="url(#drawdownFill)"
              strokeWidth={2}
              name="Drawdown"
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </ChartShell>
  );
}

// ─── Performance Classic: R-Multiple Distribution ──────────────────────────────

export function RMultipleDistributionWidget({
  data,
  isLoading,
}: {
  data?: RMultipleBucket[];
  isLoading: boolean;
}) {
  if (isLoading) return <ChartSkeleton />;

  return (
    <ChartShell
      title="R-Multiple Distribution"
      isEmpty={!data || data.length === 0}
      emptyMessage="No R-multiple distribution data available."
      helpAnchor="r-multiple-distribution"
    >
      {data && data.length > 0 && (
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="bucket_min"
              tick={{ fontSize: 10 }}
              tickFormatter={(v: string) => {
                const num = parseFloat(v);
                return isNaN(num) ? v : `${num.toFixed(1)}R`;
              }}
            />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Bar
              dataKey="count"
              fill="var(--primary)"
              radius={[4, 4, 0, 0]}
              name="Trades"
            />
          </BarChart>
        </ResponsiveContainer>
      )}
    </ChartShell>
  );
}

// ─── Execution Analysis: MAE/MFE Scatterplot ───────────────────────────────────

function renderScatterTooltip(value: unknown, name: unknown) {
  if (name === "x") return [formatCurrency(value as string | number), "MAE"];
  if (name === "y") return [formatCurrency(value as string | number), "MFE"];
  return [String(value), String(name)];
}

export const SCATTER_MAX_RAW_POINTS = 500;

export function MaeMfeScatterWidget({
  data,
  isLoading,
}: {
  data?: ScatterPoint[];
  isLoading: boolean;
}) {
  if (isLoading) return <ChartSkeleton />;

  const exceeded = data && data.length > SCATTER_MAX_RAW_POINTS;

  return (
    <ChartShell
      title="MAE / MFE"
      isEmpty={!!exceeded}
      emptyMessage={
        exceeded
          ? `Too many points (${data?.length}). Please narrow your filter to view this chart.`
          : ""
      }
      helpAnchor="mae-mfe"
    >
      {!exceeded && data && (
        <ResponsiveContainer width="100%" height={300}>
          <ScatterChart margin={{ top: 10, right: 10, bottom: 10, left: 10 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              type="number"
              dataKey="x"
              name="MAE"
              tick={{ fontSize: 11 }}
              tickFormatter={(v: number) =>
                new Intl.NumberFormat("en-US", {
                  notation: "compact",
                  compactDisplay: "short",
                }).format(v)
              }
              label={{
                value: "MAE ($)",
                position: "insideBottom",
                offset: -5,
                style: { fontSize: 11 },
              }}
            />
            <YAxis
              type="number"
              dataKey="y"
              name="MFE"
              tick={{ fontSize: 11 }}
              tickFormatter={(v: number) =>
                new Intl.NumberFormat("en-US", {
                  notation: "compact",
                  compactDisplay: "short",
                }).format(v)
              }
              label={{
                value: "MFE ($)",
                angle: -90,
                position: "insideLeft",
                style: { fontSize: 11 },
              }}
            />
            <ZAxis dataKey="count" range={[30, 300]} />
            <Tooltip
              formatter={renderScatterTooltip}
              cursor={{ strokeDasharray: "3 3" }}
            />
            <Scatter
              name="Trades"
              data={data}
              fill="var(--primary)"
              opacity={0.6}
            />
          </ScatterChart>
        </ResponsiveContainer>
      )}
    </ChartShell>
  );
}

// ─── Execution Analysis: Duration vs P&L Scatterplot ───────────────────────────

export function DurationVsPnlScatterWidget({
  data,
  isLoading,
}: {
  data?: ScatterPoint[];
  isLoading: boolean;
}) {
  if (isLoading) return <ChartSkeleton />;

  const exceeded = data && data.length > SCATTER_MAX_RAW_POINTS;

  return (
    <ChartShell
      title="Duration vs P&L"
      isEmpty={!!exceeded}
      emptyMessage={
        exceeded
          ? `Too many points (${data?.length}). Please narrow your filter to view this chart.`
          : ""
      }
      helpAnchor="duration-vs-pnl"
    >
      {!exceeded && data && (
        <ResponsiveContainer width="100%" height={300}>
          <ScatterChart margin={{ top: 10, right: 10, bottom: 10, left: 10 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              type="number"
              dataKey="x"
              name="Duration"
              tick={{ fontSize: 11 }}
              tickFormatter={(v: number) => `${v.toFixed(0)}h`}
              label={{
                value: "Duration (hours)",
                position: "insideBottom",
                offset: -5,
                style: { fontSize: 11 },
              }}
            />
            <YAxis
              type="number"
              dataKey="y"
              name="P&L"
              tick={{ fontSize: 11 }}
              tickFormatter={(v: number) =>
                new Intl.NumberFormat("en-US", {
                  notation: "compact",
                  compactDisplay: "short",
                }).format(v)
              }
              label={{
                value: "P&L ($)",
                angle: -90,
                position: "insideLeft",
                style: { fontSize: 11 },
              }}
            />
            <ZAxis dataKey="count" range={[30, 300]} />
            <Tooltip cursor={{ strokeDasharray: "3 3" }} />
            <Scatter
              name="Trades"
              data={data}
              fill="var(--primary)"
              opacity={0.6}
            />
          </ScatterChart>
        </ResponsiveContainer>
      )}
    </ChartShell>
  );
}

// ─── Attribution: Playbook vs Market Regime Heatmap ─────────────────────────────

const HEATMAP_COLORS = [
  "#f3f4f6",
  "#c7d2fe",
  "#a5b4fc",
  "#818cf8",
  "#6366f1",
  "#4f46e5",
  "#4338ca",
];

function heatColor(ratio: number): string {
  const idx = Math.min(Math.floor(ratio * (HEATMAP_COLORS.length - 1)), HEATMAP_COLORS.length - 1);
  return HEATMAP_COLORS[idx];
}

export function PlaybookPhaseHeatmapWidget({
  data,
  isLoading,
}: {
  data?: HeatmapCell[];
  isLoading: boolean;
}) {
  if (isLoading) return <ChartSkeleton />;

  const hasData = data && data.length > 0;

  if (!hasData) {
    return (
      <ChartShell
        title="Playbook vs Market Regime"
        isEmpty
        emptyMessage="No attribution data available."
        helpAnchor="checkin-attribution"
      >
        <span />
      </ChartShell>
    );
  }

  const playbooks = [...new Set(data!.map((d) => d.playbook))];
  const phases = [...new Set(data!.map((d) => d.phase))];
  const maxCount = Math.max(...data!.map((d) => d.trade_count), 1);

  return (
    <ChartShell title="Playbook vs Market Regime" isEmpty={false} helpAnchor="checkin-attribution">
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr>
              <th className="p-1 text-left text-muted-foreground font-medium">
                Playbook
              </th>
              {phases.map((phase) => (
                <th
                  key={phase}
                  className="p-1 text-center text-muted-foreground font-medium"
                >
                  {phase}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {playbooks.map((pb) => (
              <tr key={pb}>
                <td className="p-1 text-foreground font-medium whitespace-nowrap">
                  {pb}
                </td>
                {phases.map((phase) => {
                  const cell = data!.find(
                    (d) => d.playbook === pb && d.phase === phase,
                  );
                  const ratio = cell ? cell.trade_count / maxCount : 0;
                  return (
                    <td
                      key={phase}
                      className="p-1 text-center rounded-sm"
                      style={{
                        backgroundColor: heatColor(ratio),
                        color: ratio > 0.5 ? "#fff" : undefined,
                      }}
                      title={
                        cell
                          ? `${cell.trade_count} trades | WR: ${formatPercent(cell.win_rate)} | Avg: ${formatCurrency(cell.avg_pnl)}`
                          : "No data"
                      }
                    >
                      {cell ? cell.trade_count : "—"}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </ChartShell>
  );
}

// ─── Attribution: Psychological Bar Chart ──────────────────────────────────────

export function PsychologicalAttributionWidget({
  data,
  isLoading,
}: {
  data?: AttributionBar[];
  isLoading: boolean;
}) {
  if (isLoading) return <ChartSkeleton />;

  return (
    <ChartShell
      title="Psychological Attribution"
      isEmpty={!data || data.length === 0}
      emptyMessage="No psychological data available."
      helpAnchor="checkin-attribution"
    >
      {data && data.length > 0 && (
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data} layout="vertical" margin={{ left: 80 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" tick={{ fontSize: 11 }} />
            <YAxis
              type="category"
              dataKey="label"
              tick={{ fontSize: 11 }}
              width={80}
            />
            <Tooltip
              formatter={(
                _value: unknown,
                _name: unknown,
                props: unknown,
              ) => {
                const p = (props as { payload: AttributionBar }).payload;
                return [
                  p.avg_pnl
                    ? `${p.value} trades | Avg: ${formatCurrency(p.avg_pnl)}`
                    : `${p.value} trades`,
                  p.label,
                ];
              }}
            />
            <Bar dataKey="value" fill="var(--primary)" radius={[0, 4, 4, 0]} name="Trades" />
          </BarChart>
        </ResponsiveContainer>
      )}
    </ChartShell>
  );
}

// ─── Uncategorized Banner ──────────────────────────────────────────────────────

export function UncategorizedBanner({
  unmatchedCount,
  phaseUnsetCount,
}: {
  unmatchedCount: number;
  phaseUnsetCount: number;
}) {
  if (unmatchedCount === 0 && phaseUnsetCount === 0) return null;

  return (
    <div className="bg-muted/60 rounded-lg px-3 py-2 text-xs text-muted-foreground flex flex-wrap gap-x-4 gap-y-1">
      {unmatchedCount > 0 && (
        <span>
          <span className="font-medium text-foreground">{unmatchedCount}</span>{" "}
          trades without check-in
        </span>
      )}
      {phaseUnsetCount > 0 && (
        <span>
          <span className="font-medium text-foreground">{phaseUnsetCount}</span>{" "}
          trades with unset market regime
        </span>
      )}
    </div>
  );
}

// ─── Global Empty State (when no data at all) ──────────────────────────────────

export function GlobalEmptyState() {
  return (
    <div className="space-y-6">
      <EmptyState
        title="No trades match the current filters"
        description="Try adjusting your date range, playbooks, tags, or trade status to see analytics."
      />
    </div>
  );
}
