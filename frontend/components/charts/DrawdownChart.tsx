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
import { ChartShell } from "./ChartShell";
import { CHART_COLORS } from "@/lib/constants";

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
    <ChartShell title="Drawdown" isEmpty={chartData.length === 0} helpAnchor="max-drawdown">
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart
          data={chartData}
          margin={{ top: 4, right: 16, left: 8, bottom: 4 }}
        >
          <defs>
            <linearGradient id="drawdownGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={CHART_COLORS.danger} stopOpacity={0.3} />
              <stop offset="95%" stopColor={CHART_COLORS.danger} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
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
            tickFormatter={formatPercent}
            width={52}
            domain={["dataMin", 0]}
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
              return [formatPercent(num), "Drawdown"];
            }}
            labelStyle={{ color: CHART_COLORS.tooltip.label }}
          />
          <Area
            type="monotone"
            dataKey="drawdown"
            stroke={CHART_COLORS.danger}
            strokeWidth={2}
            fill="url(#drawdownGradient)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </ChartShell>
  );
}
