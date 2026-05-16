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