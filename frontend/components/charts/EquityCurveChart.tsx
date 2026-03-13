/**
 * EquityCurveChart — cumulative equity line chart using Recharts.
 */

"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { EquityCurvePoint } from "@/lib/types";

interface ChartData {
  date: string;
  equity: number;
}

interface Props {
  data: EquityCurvePoint[];
}

function formatDate(timestamp: string): string {
  return new Date(timestamp).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

function formatCurrency(value: number): string {
  return `$${value.toLocaleString("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  })}`;
}

export function EquityCurveChart({ data }: Props) {
  const chartData: ChartData[] = data.map((p) => ({
    date: formatDate(p.timestamp),
    equity: parseFloat(p.equity),
  }));

  return (
    <div className="bg-slate-800 rounded-xl p-5 border border-slate-700">
      <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wider mb-4">
        Equity Curve
      </h3>
      {chartData.length === 0 ? (
        <p className="text-slate-500 text-sm text-center py-12">
          No trade data available yet.
        </p>
      ) : (
        <ResponsiveContainer width="100%" height={280}>
          <LineChart
            data={chartData}
            margin={{ top: 4, right: 16, left: 8, bottom: 4 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis
              dataKey="date"
              tick={{ fill: "#94a3b8", fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: "#334155" }}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fill: "#94a3b8", fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: "#334155" }}
              tickFormatter={formatCurrency}
              width={72}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#0f172a",
                border: "1px solid #334155",
                borderRadius: "8px",
                color: "#f1f5f9",
              }}
              formatter={(value) => {
                const num = typeof value === "number" ? value : parseFloat(String(value));
                return [formatCurrency(num), "Equity"];
              }}
              labelStyle={{ color: "#94a3b8" }}
            />
            <Line
              type="monotone"
              dataKey="equity"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: "#3b82f6" }}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
