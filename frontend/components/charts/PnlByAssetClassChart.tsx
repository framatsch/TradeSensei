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
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={false} />
          <XAxis
            type="number"
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: "#334155" }}
            tickFormatter={formatCurrency}
          />
          <YAxis
            type="category"
            dataKey="asset_class"
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: "#334155" }}
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
          <Bar dataKey="pnl" radius={[0, 3, 3, 0]}>
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
