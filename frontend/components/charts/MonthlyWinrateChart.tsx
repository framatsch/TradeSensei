/**
 * MonthlyWinrateChart — bar chart showing monthly win rate with a 50% reference line.
 */

"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import { useMonthlyWinrate } from "@/hooks/useMonthlyWinrate";
import type { MonthlyWinratePoint } from "@/hooks/useMonthlyWinrate";
import { Spinner } from "@/components/ui/Spinner";
import { ChartShell } from "./ChartShell";

interface TooltipPayload {
  payload: MonthlyWinratePoint;
  value: number;
}

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: TooltipPayload[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-background border border-border rounded-lg px-3 py-2 text-xs">
      <p className="text-muted-foreground mb-1">{label}</p>
      <p className="text-primary font-semibold">
        Win Rate: {(parseFloat(d.win_rate) * 100).toFixed(1)}%
      </p>
      <p className="text-emerald-400">{d.win_count} wins</p>
      <p className="text-red-400">{d.loss_count} losses</p>
      <p className="text-muted-foreground">{d.trade_count} total</p>
    </div>
  );
}

export function MonthlyWinrateChart() {
  const { data, isLoading } = useMonthlyWinrate();

  if (isLoading) {
    return (
      <div className="bg-card rounded-xl p-5 border border-border">
        <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider mb-4">
          Monthly Win Rate
        </h3>
        <div className="flex items-center justify-center h-48">
          <Spinner />
        </div>
      </div>
    );
  }

  return (
    <ChartShell
      title="Monthly Win Rate"
      emptyMessage="No monthly win rate data available."
      isEmpty={!data || data.length === 0}
    >
      <ResponsiveContainer width="100%" height={240}>
        <BarChart
          data={data ?? []}
          margin={{ top: 4, right: 16, left: 8, bottom: 4 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: "#334155" }}
          />
          <YAxis
            domain={[0, 1]}
            tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: "#334155" }}
            width={44}
          />
          <ReferenceLine
            y={0.5}
            stroke="#64748b"
            strokeDasharray="4 4"
            label={{
              value: "50%",
              position: "right",
              fill: "#64748b",
              fontSize: 10,
            }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="win_rate" radius={[3, 3, 0, 0]}>
            {(data ?? []).map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={parseFloat(entry.win_rate) >= 0.5 ? "#22c55e" : "#ef4444"}
                fillOpacity={0.85}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartShell>
  );
}
