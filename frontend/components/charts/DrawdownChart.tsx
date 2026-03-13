/**
 * DrawdownChart — drawdown area chart using Recharts.
 */

"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { DrawdownPoint } from "@/lib/types";

interface ChartData {
  date: string;
  drawdown: number;
}

interface Props {
  data: DrawdownPoint[];
}

function formatDate(timestamp: string): string {
  return new Date(timestamp).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export function DrawdownChart({ data }: Props) {
  const chartData: ChartData[] = data.map((p) => ({
    date: formatDate(p.timestamp),
    drawdown: parseFloat(p.drawdown),
  }));

  return (
    <div className="bg-slate-800 rounded-xl p-5 border border-slate-700">
      <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wider mb-4">
        Drawdown
      </h3>
      {chartData.length === 0 ? (
        <p className="text-slate-500 text-sm text-center py-12">
          No trade data available yet.
        </p>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart
            data={chartData}
            margin={{ top: 4, right: 16, left: 8, bottom: 4 }}
          >
            <defs>
              <linearGradient id="drawdownGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
              </linearGradient>
            </defs>
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
              tickFormatter={formatPercent}
              width={52}
              domain={["dataMin", 0]}
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
                return [formatPercent(num), "Drawdown"];
              }}
              labelStyle={{ color: "#94a3b8" }}
            />
            <Area
              type="monotone"
              dataKey="drawdown"
              stroke="#ef4444"
              strokeWidth={2}
              fill="url(#drawdownGradient)"
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
