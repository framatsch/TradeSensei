"use client";

import { useWorkspaceFilter, useActivePortfolioId } from "@/components/workspace/WorkspaceFilterContext";
import { useScatterAnalytics } from "@/hooks/useReportingAnalytics";
import { WidgetGridSkeleton } from "@/components/reporting/ReportingSkeletons";
import dynamic from "next/dynamic";

const MaeMfeScatterWidget = dynamic(() => import("@/components/reporting/Widgets").then(mod => mod.MaeMfeScatterWidget), { ssr: false });
const DurationVsPnlScatterWidget = dynamic(() => import("@/components/reporting/Widgets").then(mod => mod.DurationVsPnlScatterWidget), { ssr: false });

export default function StrategyAnalysisPage() {
  const { filter } = useWorkspaceFilter();
  const portfolioId = useActivePortfolioId();

  const {
    data: scatterData,
    isLoading: scatterLoading,
    isError,
  } = useScatterAnalytics(portfolioId, filter);

  return (
    <div className="p-6 space-y-6">
      {isError && (
          <div className="bg-destructive/10 text-destructive px-4 py-3 rounded-md text-sm">
            Failed to load strategy analysis data.
          </div>
        )}

        {scatterLoading && !scatterData ? (
          <WidgetGridSkeleton />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <MaeMfeScatterWidget
              data={scatterData?.maeMfe}
              isLoading={scatterLoading}
            />
            <DurationVsPnlScatterWidget
              data={scatterData?.durationVsPnl}
              isLoading={scatterLoading}
            />
          </div>
        )}
    </div>
  );
}