/**
 * DailyPnlBarChart — daily PnL bar chart using Recharts.
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
import { ChartShell } from "./ChartShell";
import { CHART_COLORS } from "@/lib/constants";

interface DailyPnlBar {
  date: string;
  pnl: number;
}

interface Props {
  data: DailyPnlBar[];
}

function formatCurrency(value: number): string {
  const prefix = value >= 0 ? "+" : "";
  return `${prefix}$${Math.abs(value).toLocaleString("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  })}`;
}

export function DailyPnlBarChart({ data }: Props) {
  return (
    <ChartShell title="Daily PnL" isEmpty={data.length === 0}>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart
          data={data}
          margin={{ top: 4, right: 16, left: 8, bottom: 4 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fill: CHART_COLORS.tick, fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: CHART_COLORS.axis }}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fill: CHART_COLORS.tick, fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: CHART_COLORS.axis }}
            tickFormatter={formatCurrency}
            width={72}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: CHART_COLORS.tooltip.bg,
              border: `1px solid ${CHART_COLORS.tooltip.border}`,
              borderRadius: "8px",
              color: CHART_COLORS.tooltip.text,
            }}
            itemStyle={{ color: CHART_COLORS.tooltip.text }}
            formatter={(value) => {
              const num = typeof value === "number" ? value : parseFloat(String(value));
              return [formatCurrency(num), "PnL"];
            }}
            labelStyle={{ color: CHART_COLORS.tooltip.label }}
          />
          <Bar dataKey="pnl" radius={[2, 2, 0, 0]} barSize={20}>
            {data.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.pnl >= 0 ? CHART_COLORS.success : CHART_COLORS.danger}
                fillOpacity={0.4}
                stroke={entry.pnl >= 0 ? CHART_COLORS.success : CHART_COLORS.danger}
                strokeWidth={1}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartShell>
  );
}
