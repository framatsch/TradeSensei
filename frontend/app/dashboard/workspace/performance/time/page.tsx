"use client";

import React, { useState, useMemo } from "react";
import { useWorkspaceFilter, useActivePortfolioId } from "@/components/workspace/WorkspaceFilterContext";
import { useReportData, ReportDimension } from "@/hooks/useReportData";
import { PerformanceAnalysisDashboard } from "@/components/analytics/PerformanceAnalysisDashboard";
import { WidgetGridSkeleton } from "@/components/reporting/ReportingSkeletons";

const RESOLUTIONS: { label: string; value: ReportDimension }[] = [
  { label: "Hourly", value: "Hourly" },
  { label: "Weekday", value: "Weekday" },
  { label: "Monthly", value: "Monthly" },
  { label: "Yearly", value: "Yearly" },
];

export default function TimeAnalysisPage() {
  const { filter } = useWorkspaceFilter();
  const portfolioId = useActivePortfolioId();
  const [resolution, setResolution] = useState<ReportDimension>("Hourly");

  const { getAggregated, isLoading, isError } = useReportData(portfolioId, filter);

  const data = useMemo(() => getAggregated(resolution), [getAggregated, resolution]);

  return (
    <div className="p-6 space-y-6">
      {isError && (
        <div className="bg-destructive/10 text-destructive px-4 py-3 rounded-md text-sm">
          Failed to load time analysis data.
        </div>
      )}

      {isLoading && data.length === 0 ? (
        <WidgetGridSkeleton />
      ) : !isLoading && data.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <p className="text-base font-medium text-foreground">No data for this period</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Adjust your filters or import trades to see time analysis.
          </p>
        </div>
      ) : (
        <div className="animate-fade-in">
          <PerformanceAnalysisDashboard
            data={data}
            resolutions={RESOLUTIONS}
            activeResolution={resolution}
            onResolutionChange={(val) => setResolution(val as ReportDimension)}
            dimensionLabel={resolution}
          />
        </div>
      )}
    </div>
  );
}
