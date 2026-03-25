/**
 * Dashboard overview page — metrics summary cards + equity + drawdown charts.
 */

"use client";

import { useMetrics } from "@/hooks/useMetrics";
import { useDailyPnl } from "@/hooks/useDailyPnl";
import { useReturnDistribution } from "@/hooks/useReturnDistribution";
import { MetricsCards } from "@/components/metrics/MetricsCards";
import { EquityCurveChart } from "@/components/charts/EquityCurveChart";
import { DrawdownChart } from "@/components/charts/DrawdownChart";
import { DailyPnlBarChart } from "@/components/charts/DailyPnlBarChart";
import { ReturnDistributionChart } from "@/components/charts/ReturnDistributionChart";
import { PageHeader } from "@/components/ui/PageHeader";
import { Spinner } from "@/components/ui/Spinner";

function ChartSkeleton() {
  return (
    <div className="bg-card rounded-xl p-5 border border-border flex items-center justify-center h-48">
      <Spinner />
    </div>
  );
}

export default function DashboardPage() {
  const { data: summary, isLoading, isError, error, refetch } = useMetrics();
  const { data: dailyPnl, isLoading: loadingDaily } = useDailyPnl();
  const { data: returnDist, isLoading: loadingReturnDist } = useReturnDistribution();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner size="lg" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <p className="text-red-400 font-medium mb-2">
          Failed to load metrics.
        </p>
        <p className="text-muted-foreground text-sm mb-4">{error.message}</p>
        <button
          onClick={() => refetch()}
          className="px-4 py-2 bg-primary hover:bg-primary/90 text-white rounded-md text-sm transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Overview"
        subtitle="All-time performance metrics"
      />

      {summary ? (
        <>
          <MetricsCards
            metrics={summary.metrics}
            maxDrawdown={summary.max_drawdown}
          />

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            <EquityCurveChart data={summary.equity_curve} />
            <DrawdownChart data={summary.drawdown_curve} />
          </div>

          {/* Daily PnL and Return Distribution */}
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            {loadingDaily ? (
              <ChartSkeleton />
            ) : (
              <DailyPnlBarChart data={dailyPnl ?? []} />
            )}
            
            {loadingReturnDist ? (
              <ChartSkeleton />
            ) : (
              <ReturnDistributionChart data={returnDist ?? []} />
            )}
          </div>

        </>
      ) : (
        <div className="text-center py-20 text-muted-foreground">
          <p className="text-lg font-medium mb-2">No trades yet</p>
          <p className="text-sm">
            Import your first trades from the{" "}
            <a href="/dashboard/import" className="text-primary hover:underline">
              Import
            </a>{" "}
            page.
          </p>
        </div>
      )}
    </div>
  );
}
