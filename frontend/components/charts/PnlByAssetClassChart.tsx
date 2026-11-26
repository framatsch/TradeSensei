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
 * PnlByAssetClassChart — horizontal bar chart showing PnL by asset class.
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
import type { PnlByAssetClass } from "@/lib/types";
import { ChartShell } from "./ChartShell";
import { CHART_COLORS } from "@/lib/constants";

interface Props {
  data: PnlByAssetClass[];
}

interface ChartEntry {
  asset_class: string;
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

function toChartData(data: PnlByAssetClass[]): ChartEntry[] {
  return data.map((d) => ({
    asset_class: d.asset_class,
    pnl: parseFloat(d.total_pnl),
    trade_count: d.trade_count,
  }));
}

export function PnlByAssetClassChart({ data }: Props) {
  const chartData = toChartData(data);

  return (
    <ChartShell
      title="PnL by Asset Class"
      emptyMessage="No asset class data available yet."
      isEmpty={chartData.length === 0}
      helpAnchor="pnl-by-asset-class"
    >
      <ResponsiveContainer width="100%" height={Math.max(180, chartData.length * 44)}>
        <BarChart
          data={chartData}
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
            dataKey="asset_class"
            tick={{ fill: CHART_COLORS.tick, fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: CHART_COLORS.axis }}
            width={70}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: CHART_COLORS.tooltip.bg,
              border: `1px solid ${CHART_COLORS.tooltip.border}`,
              borderRadius: "8px",
              color: CHART_COLORS.tooltip.text,
            }}
            formatter={(value, _name, props) => {
              const num = typeof value === "number" ? value : parseFloat(String(value));
              const entry = props.payload as ChartEntry;
              return [
                `${formatCurrency(num)} (${entry.trade_count} trades)`,
                "PnL",
              ];
            }}
            labelStyle={{ color: CHART_COLORS.tooltip.label }}
          />
          <Bar dataKey="pnl" radius={[0, 3, 3, 0]}>
            {chartData.map((entry, index) => (
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
