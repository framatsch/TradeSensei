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
 * ReturnDistributionChart — histogram of trade return distribution.
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
import type { ReturnDistribution } from "@/lib/types";
import { ChartShell } from "./ChartShell";

interface Props {
  data: ReturnDistribution[];
}

interface ChartEntry {
  label: string;
  count: number;
  isPositive: boolean;
}

function formatBucketLabel(min: string, max: string): string {
  const minNum = parseFloat(min);
  const maxNum = parseFloat(max);
  const fmt = (n: number) => {
    const abs = Math.abs(n);
    const prefix = n >= 0 ? "$" : "-$";
    return `${prefix}${abs.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
  };
  return `${fmt(minNum)}–${fmt(maxNum)}`;
}

function toChartData(data: ReturnDistribution[]): ChartEntry[] {
  return data.map((d) => ({
    label: formatBucketLabel(d.bucket_min, d.bucket_max),
    count: d.count,
    isPositive: parseFloat(d.bucket_min) >= 0,
  }));
}

export function ReturnDistributionChart({ data }: Props) {
  const chartData = toChartData(data);

  return (
    <ChartShell
      title="Return Distribution"
      emptyMessage="No distribution data available yet."
      isEmpty={chartData.length === 0}
      helpAnchor="return-distribution"
    >
      <ResponsiveContainer width="100%" height={240}>
        <BarChart
          data={chartData}
          margin={{ top: 4, right: 16, left: 8, bottom: 36 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fill: "#94a3b8", fontSize: 10 }}
            tickLine={false}
            axisLine={{ stroke: "#334155" }}
            angle={-35}
            textAnchor="end"
            interval={0}
          />
          <YAxis
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: "#334155" }}
            allowDecimals={false}
            width={36}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#0f172a",
              border: "1px solid #334155",
              borderRadius: "8px",
              color: "#f1f5f9",
            }}
            formatter={(value) => [value, "Trades"]}
            labelStyle={{ color: "#94a3b8" }}
          />
          <Bar dataKey="count" radius={[3, 3, 0, 0]}>
            {chartData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.isPositive ? "#22c55e" : "#ef4444"}
                fillOpacity={0.8}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartShell>
  );
}
