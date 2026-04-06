"use client";

/**
 * TimeAnalysisTab — sub-tabbed time-based performance analysis.
 *
 * Provides Hourly / Weekday / Monthly / Yearly breakdowns using the shared
 * PerformanceAnalysisDashboard. The resolution segmented control is rendered
 * inside PerformanceAnalysisDashboard's consolidated toolbar. "View Report"
 * navigates to the trades list pre-filtered to the selected time bucket.
 */

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { PerformanceAnalysisDashboard } from "@/components/trades/PerformanceAnalysisDashboard";
import type { PerformanceDataPoint } from "@/components/trades/PerformanceAnalysisDashboard";
import { Spinner } from "@/components/ui/Spinner";
import type { Trade } from "@/lib/types";
import type { ReportDimension } from "@/hooks/useReportData";

// ─── Weekday mapping (Monday=0 … Sunday=6, matching the spec) ────────────────
const WEEKDAY_NAME_TO_INDEX: Record<string, number> = {
  Monday: 0,
  Tuesday: 1,
  Wednesday: 2,
  Thursday: 3,
  Friday: 4,
  Saturday: 5,
  Sunday: 6,
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

/** Build /dashboard/trades URL params for a time-dimension row. */
function buildTradesHref(
  row: PerformanceDataPoint,
  dimension: ReportDimension,
  trades: Trade[]
): string {
  const base = "/dashboard/trades";
  const params = new URLSearchParams();

  if (dimension === "Hourly") {
    // row.name is "09:00", "14:00" etc.
    const hour = parseInt(row.name.split(":")[0], 10);
    params.set("hour_of_day", String(hour));
    return `${base}?${params.toString()}`;
  }

  if (dimension === "Weekday") {
    const idx = WEEKDAY_NAME_TO_INDEX[row.name];
    if (idx !== undefined) params.set("day_of_week", String(idx));
    return `${base}?${params.toString()}`;
  }

  // For Monthly and Yearly we find the date range from matching trades.
  const closedTrades = trades.filter((t) => t.closed_at !== null);

  if (dimension === "Monthly") {
    // row.name is "Jan", "Feb", …
    const monthNames = [
      "Jan", "Feb", "Mar", "Apr", "May", "Jun",
      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ];
    const monthIndex = monthNames.indexOf(row.name);
    const matching = closedTrades.filter(
      (t) => new Date(t.closed_at!).getMonth() === monthIndex
    );
    if (matching.length > 0) {
      const dates = matching.map((t) => new Date(t.closed_at!).getTime());
      const from = new Date(Math.min(...dates));
      const to = new Date(Math.max(...dates));
      params.set("opened_at_from", from.toISOString());
      params.set("opened_at_to", to.toISOString());
    }
    return `${base}?${params.toString()}`;
  }

  if (dimension === "Yearly") {
    const year = parseInt(row.name, 10);
    const matching = closedTrades.filter(
      (t) => new Date(t.closed_at!).getFullYear() === year
    );
    if (matching.length > 0) {
      const dates = matching.map((t) => new Date(t.closed_at!).getTime());
      const from = new Date(Math.min(...dates));
      const to = new Date(Math.max(...dates));
      params.set("opened_at_from", from.toISOString());
      params.set("opened_at_to", to.toISOString());
    }
    return `${base}?${params.toString()}`;
  }

  return base;
}

// ─── Sub-tab config ───────────────────────────────────────────────────────────

const SUB_TABS: { label: string; value: ReportDimension }[] = [
  { label: "Yearly", value: "Yearly" },
  { label: "Monthly", value: "Monthly" },
  { label: "Weekday", value: "Weekday" },
  { label: "Hourly", value: "Hourly" },
];

// ─── Props ────────────────────────────────────────────────────────────────────

interface TimeAnalysisTabProps {
  trades: Trade[];
  isLoading: boolean;
  getAggregated: (dim: ReportDimension) => PerformanceDataPoint[];
}

// ─── Component ────────────────────────────────────────────────────────────────

export function TimeAnalysisTab({
  trades,
  isLoading,
  getAggregated,
}: TimeAnalysisTabProps) {
  const router = useRouter();
  const [activeDim, setActiveDim] = useState<ReportDimension>("Yearly");

  const data = getAggregated(activeDim);

  const handleViewReport = useCallback(
    (row: PerformanceDataPoint) => {
      router.push(buildTradesHref(row, activeDim, trades));
    },
    [router, activeDim, trades]
  );

  const handleBarClick = useCallback(
    (row: PerformanceDataPoint) => {
      router.push(buildTradesHref(row, activeDim, trades));
    },
    [router, activeDim, trades]
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <PerformanceAnalysisDashboard
      data={data}
      dimensionLabel={activeDim}
      resolutions={SUB_TABS}
      activeResolution={activeDim}
      onResolutionChange={(val) => setActiveDim(val as ReportDimension)}
      onViewReport={handleViewReport}
      onBarClick={handleBarClick}
    />
  );
}
