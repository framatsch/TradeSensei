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

"use client";

import React, { useMemo } from "react";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Line,
  ComposedChart,
} from "recharts";

interface DataPoint {
  x: number;
  y: number;
  label?: string;
}

interface ScatterWithRegressionChartProps {
  data: DataPoint[];
  xAxisLabel?: string;
  yAxisLabel?: string;
}

export function ScatterWithRegressionChart({
  data,
  xAxisLabel,
  yAxisLabel,
}: ScatterWithRegressionChartProps) {
  const chartData = useMemo(() => {
    if (!data || data.length === 0) return [];

    // Calculate regression line
    const n = data.length;
    let sumX = 0;
    let sumY = 0;
    let sumXY = 0;
    let sumXX = 0;

    data.forEach((p) => {
      sumX += p.x;
      sumY += p.y;
      sumXY += p.x * p.y;
      sumXX += p.x * p.x;
    });

    const meanX = sumX / n;
    const meanY = sumY / n;

    // Check for zero variance
    let varianceX = 0;
    data.forEach((p) => {
      varianceX += Math.pow(p.x - meanX, 2);
    });

    let slope = 0;
    let intercept = meanY;
    const hasVariance = varianceX > 0;

    if (hasVariance) {
      slope = (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX);
      intercept = meanY - slope * meanX;
    }

    // Find min and max X to draw the line
    const minX = Math.min(...data.map((d) => d.x));
    const maxX = Math.max(...data.map((d) => d.x));

    // Create unified data array for ComposedChart
    // Each point needs x, y (for scatter), and regressionY (for line)
    return data.map((d) => ({
      ...d,
      regressionY: hasVariance ? slope * d.x + intercept : null,
    }));
  }, [data]);

  if (!data || data.length === 0) {
    return (
      <div className="flex h-full w-full items-center justify-center text-sm text-muted-foreground">
        No data available
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height="100%">
      <ComposedChart
        data={chartData}
        margin={{ top: 20, right: 20, bottom: 20, left: 20 }}
      >
        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
        <XAxis
          type="number"
          dataKey="x"
          name={xAxisLabel || "X"}
          className="text-xs"
          tick={{ fill: "currentColor" }}
          tickLine={{ stroke: "currentColor" }}
        />
        <YAxis
          type="number"
          dataKey="y"
          name={yAxisLabel || "Y"}
          className="text-xs"
          tick={{ fill: "currentColor" }}
          tickLine={{ stroke: "currentColor" }}
        />
        <Tooltip
          cursor={{ strokeDasharray: "3 3" }}
          contentStyle={{
            backgroundColor: "hsl(var(--background))",
            borderColor: "hsl(var(--border))",
            borderRadius: "var(--radius)",
          }}
        />
        <Scatter name="Data" dataKey="y" fill="hsl(var(--primary))" />
        <Line
          type="monotone"
          dataKey="regressionY"
          stroke="hsl(var(--destructive))"
          dot={false}
          activeDot={false}
          isAnimationActive={false}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
