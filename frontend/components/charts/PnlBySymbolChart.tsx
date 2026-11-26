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
 * PnlBySymbolChart — horizontal bar chart showing PnL by symbol.
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

interface SymbolPnl {
  symbol: string;
  pnl: number;
}

interface Props {
  data: SymbolPnl[];
}

function formatCurrency(value: number): string {
  const prefix = value >= 0 ? "+" : "";
  return `${prefix}$${Math.abs(value).toLocaleString("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  })}`;
}

export function PnlBySymbolChart({ data }: Props) {
  return (
    <ChartShell title="PnL by Symbol" isEmpty={data.length === 0} helpAnchor="pnl-by-symbol">
      <ResponsiveContainer width="100%" height={Math.max(200, data.length * 36)}>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 4, right: 24, left: 8, bottom: 4 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} horizontal={false} />
          <XAxis
            type="number"
            tick={{ fill: CHART_COLORS.tick, fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: CHART_COLORS.axis }}
            tickFormatter={formatCurrency}
          />
          <YAxis
            type="category"
            dataKey="symbol"
            tick={{ fill: CHART_COLORS.tick, fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: CHART_COLORS.axis }}
            width={60}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: CHART_COLORS.tooltip.bg,
              border: `1px solid ${CHART_COLORS.tooltip.border}`,
              borderRadius: "8px",
              color: CHART_COLORS.tooltip.text,
            }}
            formatter={(value) => {
              const num = typeof value === "number" ? value : parseFloat(String(value));
              return [formatCurrency(num), "PnL"];
            }}
            labelStyle={{ color: CHART_COLORS.tooltip.label }}
          />
          <Bar dataKey="pnl" radius={[0, 3, 3, 0]}>
            {data.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.pnl >= 0 ? CHART_COLORS.success : CHART_COLORS.danger}
                fillOpacity={0.85}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartShell>
  );
}
