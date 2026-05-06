"use client";

import { useMemo } from "react";
import { useWorkspaceFilter, useActivePortfolioId } from "@/components/workspace/WorkspaceFilterContext";
import {
  useAnalyticsSummary,
  useMarketPhaseCorrelation,
  useReturnDistribution,
} from "@/hooks/useReportingAnalytics";
import { WidgetGridSkeleton } from "@/components/reporting/ReportingSkeletons";
import { GlobalEmptyState, UncategorizedBanner, MetricCard } from "@/components/reporting/Widgets";
import dynamic from "next/dynamic";
import type { HeatmapCell, AttributionBar } from "@/components/reporting/Widgets";
import type { MarketPhaseCorrelation } from "@/lib/api/types.gen";

const RMultipleDistributionWidget = dynamic(() => import("@/components/reporting/Widgets").then(mod => mod.RMultipleDistributionWidget), { ssr: false });
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

export default function WorkspaceReportingPage() {
  const { filter } = useWorkspaceFilter();
  const portfolioId = useActivePortfolioId();

  const {
    data: summary,
    isLoading: summaryLoading,
    isError: summaryError,
  } = useAnalyticsSummary(portfolioId, filter, filter.viewId);

  const {
    data: attribution,
    isLoading: attributionLoading,
  } = useMarketPhaseCorrelation(portfolioId, filter, filter.viewId);

  const { data: returnDistribution, isLoading: distributionLoading } =
    useReturnDistribution(portfolioId, filter);

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

  const distributionData = useMemo(
    () =>
      returnDistribution?.map((d) => ({
        bucket_min: String(d.bucket_min),
        bucket_max: String(d.bucket_max),
        count: d.count,
      })),
    [returnDistribution],
  );

  const isLoading = summaryLoading;
  const isInitialLoading = summaryLoading && !summary;

  return (
    <div className="p-6 space-y-6 pt-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Reporting Hub</h1>
      </div>

      {summaryError && (
        <div className="bg-destructive/10 text-destructive px-4 py-3 rounded-md text-sm">
          Failed to load reporting data.
        </div>
      )}

        {isInitialLoading && <WidgetGridSkeleton />}

        {!isInitialLoading &&
          summary &&
          !summary.total_trades &&
          (!attribution || attribution.buckets.length === 0) && (
            <GlobalEmptyState />
          )}

        {!isInitialLoading && (
          <div className="space-y-6 animate-fade-in">
            {summary && (
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
                <MetricCard label="Win Rate" value={`${(parseFloat(summary.win_rate) * 100).toFixed(1)}%`} />
                <MetricCard label="Profit Factor" value={summary.profit_factor ? parseFloat(summary.profit_factor).toFixed(2) : "—"} />
                <MetricCard label="Total Trades" value={String(summary.total_trades)} />
                <MetricCard label="Gross Profit" value={summary.gross_profit ? `$${summary.gross_profit}` : "—"} trend="up" />
                <MetricCard label="Gross Loss" value={summary.gross_loss ? `$${summary.gross_loss}` : "—"} trend="down" />
              </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <RMultipleDistributionWidget
                data={distributionData}
                isLoading={distributionLoading}
              />
              <PsychologicalAttributionWidget
                data={attributionBars}
                isLoading={attributionLoading}
              />
            </div>

            <UncategorizedBanner
              unmatchedCount={attribution?.unmatched_trade_count ?? 0}
              phaseUnsetCount={attribution?.phase_unset_trade_count ?? 0}
            />

            <div className="grid grid-cols-1 gap-4">
              <PlaybookPhaseHeatmapWidget
                data={heatmapCells}
                isLoading={attributionLoading}
              />
            </div>
          </div>
        )}
    </div>
  );
}