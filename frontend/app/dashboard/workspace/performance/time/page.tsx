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
