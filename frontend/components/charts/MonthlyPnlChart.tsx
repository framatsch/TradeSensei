/**
 * MonthlyPnlChart — bar chart of monthly PnL with green/red coloring.
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
  ResponsiveContainer,
} from "recharts";
import type { MonthlyPnl } from "@/lib/types";
import { ChartShell } from "./ChartShell";

interface Props {
  data: MonthlyPnl[];
}

interface ChartEntry {
  label: string;
  pnl: number;
  trade_count: number;
}

function formatCurrency(value: number): string {
  const prefix = value >= 0 ? "+" : "";
  return `${prefix}$${Math.abs(value).toLocaleString("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  })}`;
}

function toChartData(data: MonthlyPnl[]): ChartEntry[] {
  return data.map((d) => ({
    label: new Date(d.year, d.month - 1).toLocaleDateString("en-US", {
      month: "short",
      year: "numeric",
    }),
    pnl: parseFloat(d.pnl),
    trade_count: d.trade_count,
  }));
}

export function MonthlyPnlChart({ data }: Props) {
  const chartData = toChartData(data);

  return (
    <ChartShell
      title="Monthly PnL"
      emptyMessage="No monthly data available."
      isEmpty={chartData.length === 0}
    >
      <ResponsiveContainer width="100%" height={240}>
        <BarChart
          data={chartData}
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
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: "#334155" }}
            tickFormatter={formatCurrency}
            width={70}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#0f172a",
              border: "1px solid #334155",
              borderRadius: "8px",
              color: "#f1f5f9",
            }}
            formatter={(value, _name, props) => {
              const num = typeof value === "number" ? value : parseFloat(String(value));
              const entry = props.payload as ChartEntry;
              return [
                `${formatCurrency(num)} (${entry.trade_count} trades)`,
                "PnL",
              ];
            }}
            labelStyle={{ color: "#94a3b8" }}
          />
          <Bar dataKey="pnl" radius={[3, 3, 0, 0]}>
            {chartData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.pnl >= 0 ? "#22c55e" : "#ef4444"}
                fillOpacity={0.85}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartShell>
  );
}
