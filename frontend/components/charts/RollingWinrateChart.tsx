/**
 * RollingWinrateChart — line chart showing rolling win rate over trades.
 * Includes a dashed 50% reference line and a window size selector.
 */

"use client";

import { useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import { useRollingWinrate } from "@/hooks/useRollingWinrate";
import { Spinner } from "@/components/ui/Spinner";

const WINDOW_OPTIONS = [10, 20, 50] as const;
type WindowOption = (typeof WINDOW_OPTIONS)[number];

interface TooltipPayload {
  trade_index: number;
  closed_at: string;
  rolling_winrate: number;
  window: number;
}

function CustomTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: TooltipPayload }>;
}) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-background border border-border rounded-lg px-3 py-2 text-xs">
      <p className="text-muted-foreground mb-1">
        Trade #{d.trade_index} &middot;{" "}
        {new Date(d.closed_at).toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
          year: "numeric",
        })}
      </p>
      <p className="text-primary font-semibold">
        Win Rate: {(d.rolling_winrate * 100).toFixed(1)}%
      </p>
      <p className="text-muted-foreground">Window: {d.window} trades</p>
    </div>
  );
}

export function RollingWinrateChart() {
  const [window, setWindow] = useState<WindowOption>(20);
  const { data, isLoading } = useRollingWinrate(window);

  return (
    <div className="bg-card rounded-xl p-5 border border-border">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
          Rolling Win Rate
        </h3>
        <div className="flex items-center gap-1">
          {WINDOW_OPTIONS.map((w) => (
            <button
              key={w}
              type="button"
              onClick={() => setWindow(w)}
              className={`px-2.5 py-1 text-xs rounded-md transition-colors ${
                window === w
                  ? "bg-primary text-white"
                  : "bg-secondary text-muted-foreground hover:text-foreground hover:bg-slate-200 dark:bg-slate-600"
              }`}
            >
              {w}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-48">
          <Spinner />
        </div>
      ) : !data || data.length === 0 ? (
        <p className="text-muted-foreground text-sm text-center py-12">
          Not enough trades to compute rolling win rate.
        </p>
      ) : (
        <ResponsiveContainer width="100%" height={240}>
          <LineChart
            data={data}
            margin={{ top: 4, right: 16, left: 8, bottom: 4 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
            <XAxis
              dataKey="trade_index"
              tick={{ fill: "#94a3b8", fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: "#334155" }}
              label={{
                value: "Trade #",
                position: "insideBottomRight",
                offset: -4,
                fill: "#64748b",
                fontSize: 10,
              }}
            />
            <YAxis
              domain={[0, 1]}
              tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
              tick={{ fill: "#94a3b8", fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: "#334155" }}
              width={44}
            />
            <ReferenceLine
              y={0.5}
              stroke="#64748b"
              strokeDasharray="4 4"
              label={{
                value: "50%",
                position: "right",
                fill: "#64748b",
                fontSize: 10,
              }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Line
              type="monotone"
              dataKey="rolling_winrate"
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
