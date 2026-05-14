"use client";

import React from "react";
import { ResponsiveContainer } from "recharts";

export interface HeatmapDataPoint {
  x: string;
  y: string;
  value: number;
}

interface CoOccurrenceHeatmapProps {
  data: HeatmapDataPoint[];
  xAxisName: string;
  yAxisName: string;
}

const InnerHeatmap = ({
  width,
  height,
  data,
  xAxisName,
  yAxisName,
}: CoOccurrenceHeatmapProps & { width?: number; height?: number }) => {
  if (!width || !height) return <div />;

  const xLabels = Array.from(new Set(data.map((d) => d.x))).sort();
  const yLabels = Array.from(new Set(data.map((d) => d.y))).sort();

  const padding = { top: 20, right: 20, bottom: 60, left: 60 };
  const innerWidth = width - padding.left - padding.right;
  const innerHeight = height - padding.top - padding.bottom;

  const cellWidth = innerWidth / Math.max(xLabels.length, 1);
  const cellHeight = innerHeight / Math.max(yLabels.length, 1);

  const maxVal = Math.max(...data.map((d) => d.value), 1);

  return (
    <svg width={width} height={height} className="text-xs">
      {/* Y Axis Labels */}
      {yLabels.map((label, i) => (
        <text
          key={`y-${label}`}
          x={padding.left - 10}
          y={padding.top + i * cellHeight + cellHeight / 2}
          textAnchor="end"
          alignmentBaseline="middle"
          fill="currentColor"
          className="text-muted-foreground"
        >
          {label}
        </text>
      ))}

      {/* X Axis Labels */}
      {xLabels.map((label, i) => (
        <g
          key={`x-${label}`}
          transform={`translate(${padding.left + i * cellWidth + cellWidth / 2}, ${height - padding.bottom + 10})`}
        >
          <text
            textAnchor="end"
            alignmentBaseline="middle"
            fill="currentColor"
            transform="rotate(-45)"
            className="text-muted-foreground"
          >
            {label}
          </text>
        </g>
      ))}

      {/* Cells */}
      {xLabels.map((x, i) =>
        yLabels.map((y, j) => {
          const pt = data.find((d) => d.x === x && d.y === y);
          const val = pt ? pt.value : 0;
          const opacity = val / maxVal;

          return (
            <g key={`${x}-${y}`}>
              <rect
                x={padding.left + i * cellWidth}
                y={padding.top + j * cellHeight}
                width={cellWidth - 2}
                height={cellHeight - 2}
                fill={`rgba(59, 130, 246, ${opacity * 0.8 + 0.05})`}
                rx={4}
                className="transition-colors hover:fill-blue-500"
              >
                <title>{`${y} / ${x}: ${val} trades`}</title>
              </rect>
              {val > 0 && (
                <text
                  x={padding.left + i * cellWidth + cellWidth / 2}
                  y={padding.top + j * cellHeight + cellHeight / 2}
                  textAnchor="middle"
                  alignmentBaseline="middle"
                  className={opacity > 0.5 ? "fill-white" : "fill-foreground"}
                  pointerEvents="none"
                >
                  {val}
                </text>
              )}
            </g>
          );
        })
      )}
    </svg>
  );
};

export function CoOccurrenceHeatmap({
  data,
  xAxisName,
  yAxisName,
}: CoOccurrenceHeatmapProps) {
  if (data.length === 0) return null;

  return (
    <ResponsiveContainer width="100%" height="100%">
      <InnerHeatmap data={data} xAxisName={xAxisName} yAxisName={yAxisName} />
    </ResponsiveContainer>
  );
}
