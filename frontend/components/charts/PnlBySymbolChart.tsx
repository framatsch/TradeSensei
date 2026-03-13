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
    <div className="bg-slate-800 rounded-xl p-5 border border-slate-700">
      <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wider mb-4">
        PnL by Symbol
      </h3>
      {data.length === 0 ? (
        <p className="text-slate-500 text-sm text-center py-12">
          No trade data available yet.
        </p>
      ) : (
        <ResponsiveContainer width="100%" height={Math.max(200, data.length * 36)}>
          <BarChart
            data={data}
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
              dataKey="symbol"
              tick={{ fill: "#94a3b8", fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: "#334155" }}
              width={60}
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
                return [formatCurrency(num), "PnL"];
              }}
              labelStyle={{ color: "#94a3b8" }}
            />
            <Bar dataKey="pnl" radius={[0, 3, 3, 0]}>
              {data.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.pnl >= 0 ? "#22c55e" : "#ef4444"}
                  fillOpacity={0.85}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
