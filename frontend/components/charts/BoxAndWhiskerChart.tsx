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

import React from "react";
import {
  ComposedChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ErrorBar,
  Scatter,
} from "recharts";

export interface BoxPlotData {
  category: string;
  min: number;
  q1: number;
  median: number;
  q3: number;
  max: number;
  outliers: number[];
  count: number;
  rawValues?: number[]; // For dot plot when N < 3
}

interface BoxAndWhiskerChartProps {
  data: BoxPlotData[];
  xAxisLabel?: string;
  yAxisLabel?: string;
}

const CustomBox = (props: any) => {
  const { x, y, width, height, q1, median, q3, payload } = props;

  if (payload.count < 3) return null; // handled by dot plot

  // Recharts Bar gives us y and height based on the [q1, q3] array we pass, 
  // but to be precise, we can draw it manually if we have full scale access.
  // For simplicity, assuming the Bar dataKey="box" is [q1, q3]
  return (
    <g>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        fill="hsl(var(--primary) / 0.2)"
        stroke="hsl(var(--primary))"
      />
      {/* Median line */}
      {/* Note: In a fully custom shape we might need scale to find exact median Y, 
          but for now we pass it as a prop or rely on the standard Bar behavior if we map it correctly. 
          To do it robustly in Recharts, a custom shape needs the scale. */}
    </g>
  );
};

export function BoxAndWhiskerChart({
  data,
  xAxisLabel,
  yAxisLabel,
}: BoxAndWhiskerChartProps) {
  // Transform data for Recharts ComposedChart
  const chartData = data.map((d) => {
    return {
      category: d.category,
      // For the Bar (Q1 to Q3)
      box: [d.q1, d.q3],
      // For ErrorBar (whiskers) - wait, ErrorBar is typically attached to a Line or Scatter.
      // We can attach it to a hidden Scatter at the median.
      median: d.median,
      // ErrorBar needs [lower, upper] relative to the value, or absolute if mapped correctly depending on Recharts version.
      // In newer recharts, error bar data can be absolute or relative. Let's provide relative to median.
      error: d.count >= 3 ? [d.median - d.min, d.max - d.median] : null,
      outliers: d.outliers.map(val => ({ x: d.category, y: val })),
      rawDots: d.count < 3 && d.rawValues ? d.rawValues.map(val => ({ x: d.category, y: val })) : [],
      count: d.count,
    };
  });

  // Flatten outliers and raw dots for Scatter
  const outliersData = chartData.flatMap(d => d.outliers);
  const rawDotsData = chartData.flatMap(d => d.rawDots);

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
          dataKey="category"
          name={xAxisLabel || "Category"}
          className="text-xs"
          tick={{ fill: "currentColor" }}
        />
        <YAxis
          name={yAxisLabel || "Value"}
          className="text-xs"
          tick={{ fill: "currentColor" }}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "hsl(var(--background))",
            borderColor: "hsl(var(--border))",
            borderRadius: "var(--radius)",
          }}
        />
        
        {/* Box for Q1-Q3 */}
        <Bar dataKey="box" fill="hsl(var(--primary) / 0.5)" stroke="hsl(var(--primary))" />
        
        {/* Median and Whiskers */}
        <Scatter dataKey="median" fill="hsl(var(--primary))" opacity={0}>
          <ErrorBar dataKey="error" width={10} strokeWidth={2} stroke="hsl(var(--primary))" />
        </Scatter>
        
        {/* Outliers */}
        <Scatter data={outliersData} dataKey="y" fill="hsl(var(--destructive))" />
        
        {/* Dot plot for N < 3 */}
        <Scatter data={rawDotsData} dataKey="y" fill="hsl(var(--primary))" />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
