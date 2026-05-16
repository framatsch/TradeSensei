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

import { useMemo } from "react";
import { useWorkspaceFilter, useActivePortfolioId } from "@/components/workspace/WorkspaceFilterContext";
import { useMarketPhaseCorrelation } from "@/hooks/useReportingAnalytics";
import { WidgetGridSkeleton } from "@/components/reporting/ReportingSkeletons";
import { UncategorizedBanner } from "@/components/reporting/Widgets";
import dynamic from "next/dynamic";
import type { HeatmapCell, AttributionBar } from "@/components/reporting/Widgets";
import type { MarketPhaseCorrelation } from "@/lib/api/types.gen";

const PlaybookPhaseHeatmapWidget = dynamic(() => import("@/components/reporting/Widgets").then(mod => mod.PlaybookPhaseHeatmapWidget), { ssr: false });
const PsychologicalAttributionWidget = dynamic(() => import("@/components/reporting/Widgets").then(mod => mod.PsychologicalAttributionWidget), { ssr: false });

function toHeatmapCells(
  buckets: MarketPhaseCorrelation[] | undefined,
  unmatchedCount: number,
): HeatmapCell[] {
  const cells: HeatmapCell[] = [];
  if (buckets) {
    cells.push(
      ...buckets.map((b) => ({
        playbook: b.label ?? "Unknown",
        phase: b.market_phase ?? "Unset",
        trade_count: b.trade_count,
        win_rate: b.win_rate,
        avg_pnl: b.avg_pnl ?? "0",
      }))
    );
  }
  if (unmatchedCount > 0) {
    cells.push({
      playbook: "Uncategorized",
      phase: "Uncategorized",
      trade_count: unmatchedCount,
      win_rate: "0",
      avg_pnl: "0",
    });
  }
  return cells;
}

function toAttributionBars(
  buckets: MarketPhaseCorrelation[] | undefined,
  unmatchedCount: number,
  phaseUnsetCount: number,
): AttributionBar[] {
  const bars: AttributionBar[] = [];
  if (buckets) {
    for (const b of buckets) {
      bars.push({
        label: b.label ?? "Unknown",
        value: b.trade_count,
        avg_pnl: b.avg_pnl ?? undefined,
        win_rate: b.win_rate,
      });
    }
  }
  if (unmatchedCount > 0) {
    bars.push({
      label: "Uncategorized",
      value: unmatchedCount,
    });
  }
  if (phaseUnsetCount > 0) {
    bars.push({
      label: "Phase Unset",
      value: phaseUnsetCount,
    });
  }
  return bars;
}

export default function BehaviorAnalysisPage() {
  const { filter } = useWorkspaceFilter();
  const portfolioId = useActivePortfolioId();

  const {
    data: attribution,
    isLoading,
    isError,
  } = useMarketPhaseCorrelation(portfolioId, filter, filter.viewId);

  const heatmapCells = useMemo(
    () => toHeatmapCells(attribution?.buckets, attribution?.unmatched_trade_count ?? 0),
    [attribution],
  );

  const attributionBars = useMemo(
    () =>
      toAttributionBars(
        attribution?.buckets,
        attribution?.unmatched_trade_count ?? 0,
        attribution?.phase_unset_trade_count ?? 0,
      ),
    [attribution],
  );

  return (
    <div className="p-6 space-y-6">
      {isError && (
          <div className="bg-destructive/10 text-destructive px-4 py-3 rounded-md text-sm">
            Failed to load behavior analysis data.
          </div>
        )}

        {isLoading && !attribution ? (
          <WidgetGridSkeleton />
        ) : (
          <div className="space-y-6 animate-fade-in">
            <div className="grid grid-cols-1 gap-4">
              <PsychologicalAttributionWidget
                data={attributionBars}
                isLoading={isLoading}
              />
            </div>

            <UncategorizedBanner
              unmatchedCount={attribution?.unmatched_trade_count ?? 0}
              phaseUnsetCount={attribution?.phase_unset_trade_count ?? 0}
            />

            <div className="grid grid-cols-1 gap-4">
              <PlaybookPhaseHeatmapWidget
                data={heatmapCells}
                isLoading={isLoading}
              />
            </div>
          </div>
        )}
    </div>
  );
}