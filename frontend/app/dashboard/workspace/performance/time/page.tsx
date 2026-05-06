"use client";

import React, { useState, useMemo } from "react";
import { useWorkspaceFilter } from "@/components/workspace/WorkspaceFilterContext";
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
  const [resolution, setResolution] = useState<ReportDimension>("Hourly");

  const { getAggregated, isLoading, isError } = useReportData(filter.portfolioId, filter);

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
