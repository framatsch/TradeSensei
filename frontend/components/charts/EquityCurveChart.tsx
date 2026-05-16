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
 * EquityCurveChart — cumulative equity line chart using Recharts.
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
import type { EquityCurvePoint } from "@/lib/types";
import { ChartShell } from "./ChartShell";
import { CHART_COLORS } from "@/lib/constants";

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
    <ChartShell title="Equity Curve" isEmpty={chartData.length === 0} helpAnchor="equity-curve">
      <ResponsiveContainer width="100%" height={280}>
        <AreaChart
          data={chartData}
          margin={{ top: 4, right: 16, left: 8, bottom: 4 }}
        >
          <defs>
            <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={CHART_COLORS.primary} stopOpacity={0.2} />
              <stop offset="95%" stopColor={CHART_COLORS.primary} stopOpacity={0} />
            </linearGradient>
          </defs>
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
              return [formatCurrency(num), "Equity"];
            }}
            labelStyle={{ color: CHART_COLORS.tooltip.label }}
          />
          <Area
            type="monotone"
            dataKey="equity"
            stroke={CHART_COLORS.primary}
            strokeWidth={2}
            fill="url(#equityGradient)"
            activeDot={{ r: 4, fill: CHART_COLORS.primary }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </ChartShell>
  );
}
