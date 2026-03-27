"use client";

/**
 * TimeAnalysisTab — sub-tabbed time-based performance analysis.
 *
 * Provides Hourly / Weekday / Monthly / Yearly breakdowns using the shared
 * PerformanceAnalysisDashboard. "View Report" navigates to the trades list
 * pre-filtered to the selected time bucket.
 */

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { PerformanceAnalysisDashboard } from "@/components/trades/PerformanceAnalysisDashboard";
import type { PerformanceDataPoint } from "@/components/trades/PerformanceAnalysisDashboard";
import { AccountFilter } from "@/components/ui/AccountFilter";
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

// Sunday=0 in JS Date, but the spec wants Monday=0
const JS_DAY_TO_SPEC_INDEX: Record<number, number> = {
  0: 6, // Sunday → 6
  1: 0, // Monday → 0
  2: 1,
  3: 2,
  4: 3,
  5: 4,
  6: 5, // Saturday → 5
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
  { label: "Hourly", value: "Hourly" },
  { label: "Weekday", value: "Weekday" },
  { label: "Monthly", value: "Monthly" },
  { label: "Yearly", value: "Yearly" },
];

// ─── Props ────────────────────────────────────────────────────────────────────

interface TimeAnalysisTabProps {
  trades: Trade[];
  isLoading: boolean;
  getAggregated: (dim: ReportDimension) => PerformanceDataPoint[];
  accountId: string | null;
  onAccountChange: (id: string | null) => void;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function TimeAnalysisTab({
  trades,
  isLoading,
  getAggregated,
  accountId,
  onAccountChange,
}: TimeAnalysisTabProps) {
  const router = useRouter();
  const [activeDim, setActiveDim] = useState<ReportDimension>("Hourly");

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

  return (
    <div className="flex flex-col gap-6">
      {/* Controls row: account filter + sub-tab bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        {/* Sub-tab pill bar */}
        <div className="inline-flex items-center gap-1 rounded-lg border border-border bg-muted/40 p-1">
          {SUB_TABS.map((tab) => (
            <button
              key={tab.value}
              onClick={() => setActiveDim(tab.value)}
              className={[
                "px-4 py-1.5 rounded-md text-sm font-medium transition-all",
                activeDim === tab.value
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted/60",
              ].join(" ")}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Account filter */}
        <AccountFilter value={accountId} onChange={onAccountChange} />
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex items-center justify-center py-24">
          <Spinner size="lg" />
        </div>
      ) : (
        <PerformanceAnalysisDashboard
          data={data}
          dimensionLabel={activeDim}
          onViewReport={handleViewReport}
          onBarClick={handleBarClick}
        />
      )}
    </div>
  );
}
