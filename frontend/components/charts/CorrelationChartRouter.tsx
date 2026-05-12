"use client";

import React from "react";
import { ScatterWithRegressionChart } from "./ScatterWithRegressionChart";
import { BoxAndWhiskerChart, BoxPlotData } from "./BoxAndWhiskerChart";
import { CoOccurrenceHeatmap, HeatmapDataPoint } from "./CoOccurrenceHeatmap";

type DataType = "continuous" | "categorical";

interface RawDataPoint {
  x: number | string;
  y: number | string;
}

interface CorrelationChartRouterProps {
  x_axis_data_type: DataType;
  y_axis_data_type: DataType;
  data_points: RawDataPoint[];
  xAxisLabel?: string;
  yAxisLabel?: string;
}

export function CorrelationChartRouter({
  x_axis_data_type,
  y_axis_data_type,
  data_points,
  xAxisLabel,
  yAxisLabel,
}: CorrelationChartRouterProps) {
  if (!data_points || data_points.length === 0) {
    return (
      <div className="flex h-full w-full items-center justify-center text-sm text-muted-foreground">
        No data available
      </div>
    );
  }

  // continuous vs continuous -> ScatterWithRegressionChart
  if (x_axis_data_type === "continuous" && y_axis_data_type === "continuous") {
    const formattedData = data_points.map((d) => ({
      x: Number(d.x),
      y: Number(d.y),
    }));

    return (
      <ScatterWithRegressionChart
        data={formattedData}
        xAxisLabel={xAxisLabel}
        yAxisLabel={yAxisLabel}
      />
    );
  }

  // categorical vs continuous -> BoxAndWhiskerChart
  if (
    (x_axis_data_type === "categorical" && y_axis_data_type === "continuous") ||
    (x_axis_data_type === "continuous" && y_axis_data_type === "categorical")
  ) {
    const isCatX = x_axis_data_type === "categorical";
    const grouped = data_points.reduce((acc, point) => {
      const cat = String(isCatX ? point.x : point.y);
      const val = Number(isCatX ? point.y : point.x);
      if (!acc[cat]) acc[cat] = [];
      acc[cat].push(val);
      return acc;
    }, {} as Record<string, number[]>);

    const boxData: BoxPlotData[] = Object.entries(grouped).map(([category, values]) => {
      values.sort((a, b) => a - b);
      const count = values.length;
      
      const quantile = (q: number) => {
        const pos = (values.length - 1) * q;
        const base = Math.floor(pos);
        const rest = pos - base;
        if (values[base + 1] !== undefined) {
          return values[base] + rest * (values[base + 1] - values[base]);
        } else {
          return values[base];
        }
      };

      const q1 = count >= 3 ? quantile(0.25) : 0;
      const median = count >= 3 ? quantile(0.5) : 0;
      const q3 = count >= 3 ? quantile(0.75) : 0;
      const iqr = q3 - q1;
      const lowerFence = q1 - 1.5 * iqr;
      const upperFence = q3 + 1.5 * iqr;

      const nonOutliers = values.filter((v) => v >= lowerFence && v <= upperFence);
      const min = count >= 3 ? Math.min(...nonOutliers) : 0;
      const max = count >= 3 ? Math.max(...nonOutliers) : 0;
      const outliers = count >= 3 ? values.filter((v) => v < lowerFence || v > upperFence) : [];

      return {
        category,
        count,
        min,
        q1,
        median,
        q3,
        max,
        outliers,
        rawValues: count < 3 ? values : undefined,
      };
    });

    return (
      <BoxAndWhiskerChart
        data={boxData}
        xAxisLabel={isCatX ? xAxisLabel : yAxisLabel}
        yAxisLabel={isCatX ? yAxisLabel : xAxisLabel}
      />
    );
  }

  // categorical vs categorical -> CoOccurrenceHeatmap
  if (x_axis_data_type === "categorical" && y_axis_data_type === "categorical") {
    const frequencies: Record<string, number> = {};
    data_points.forEach((p) => {
      const key = `${p.x}|${p.y}`;
      frequencies[key] = (frequencies[key] || 0) + 1;
    });

    const heatmapData: HeatmapDataPoint[] = Object.entries(frequencies).map(([key, value]) => {
      const [x, y] = key.split("|");
      return { x, y, value };
    });

    return (
        <CoOccurrenceHeatmap
          data={heatmapData}
          xAxisName={xAxisLabel || ""}
          yAxisName={yAxisLabel || ""}
        />
    );
  }

  return (
    <div className="flex h-full w-full items-center justify-center text-sm text-muted-foreground">
      Unsupported chart type combination
    </div>
  );
}
