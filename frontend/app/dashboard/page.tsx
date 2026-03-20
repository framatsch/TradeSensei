/**
 * Dashboard overview page — metrics summary cards + equity + drawdown charts.
 */

"use client";

import { useMetrics } from "@/hooks/useMetrics";
import { useDailyPnl } from "@/hooks/useDailyPnl";
import { useMonthlyPnl } from "@/hooks/useMonthlyPnl";
import { usePnlByAssetClass } from "@/hooks/usePnlByAssetClass";
import { usePnlBySymbol } from "@/hooks/usePnlBySymbol";
import { useReturnDistribution } from "@/hooks/useReturnDistribution";
import { MetricsCards } from "@/components/metrics/MetricsCards";
import { EquityCurveChart } from "@/components/charts/EquityCurveChart";
import { DrawdownChart } from "@/components/charts/DrawdownChart";
import { DailyPnlBarChart } from "@/components/charts/DailyPnlBarChart";
import { MonthlyPnlChart } from "@/components/charts/MonthlyPnlChart";
import { PnlByAssetClassChart } from "@/components/charts/PnlByAssetClassChart";
import { PnlBySymbolChart } from "@/components/charts/PnlBySymbolChart";
import { ReturnDistributionChart } from "@/components/charts/ReturnDistributionChart";
import { RollingWinrateChart } from "@/components/charts/RollingWinrateChart";
import { MonthlyWinrateChart } from "@/components/charts/MonthlyWinrateChart";
import { PageHeader } from "@/components/ui/PageHeader";
import { Spinner } from "@/components/ui/Spinner";

function ChartSkeleton() {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl p-5 border border-slate-200 dark:border-slate-700 flex items-center justify-center h-48">
      <Spinner />
    </div>
  );
}

export default function DashboardPage() {
  const { data: summary, isLoading, isError, error, refetch } = useMetrics();
  const { data: dailyPnl, isLoading: loadingDaily } = useDailyPnl();
  const { data: monthlyPnl, isLoading: loadingMonthly } = useMonthlyPnl();
  const { data: pnlByAssetClass, isLoading: loadingAssetClass } = usePnlByAssetClass();
  const { data: pnlBySymbol, isLoading: loadingBySymbol } = usePnlBySymbol();
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
        <p className="text-slate-500 text-sm mb-4">{error.message}</p>
        <button
          onClick={() => refetch()}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm transition-colors"
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

          {/* Daily PnL */}
          <div className="mt-2">
            {loadingDaily ? (
              <ChartSkeleton />
            ) : (
              <DailyPnlBarChart data={dailyPnl ?? []} />
            )}
          </div>

          {/* Monthly PnL — full width row */}
          <div>
            {loadingMonthly ? (
              <ChartSkeleton />
            ) : (
              <MonthlyPnlChart data={monthlyPnl ?? []} />
            )}
          </div>

          {/* Three-column row: PnL by Asset Class, Return Distribution, PnL by Symbol */}
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
            {loadingAssetClass ? (
              <ChartSkeleton />
            ) : (
              <PnlByAssetClassChart data={pnlByAssetClass ?? []} />
            )}

            {loadingReturnDist ? (
              <ChartSkeleton />
            ) : (
              <ReturnDistributionChart data={returnDist ?? []} />
            )}

            {loadingBySymbol ? (
              <ChartSkeleton />
            ) : (
              <PnlBySymbolChart
                data={(pnlBySymbol ?? []).map((d) => ({
                  symbol: d.symbol,
                  pnl: parseFloat(d.total_pnl),
                }))}
              />
            )}
          </div>

          {/* Win Rate Development */}
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            <RollingWinrateChart />
            <MonthlyWinrateChart />
          </div>
        </>
      ) : (
        <div className="text-center py-20 text-slate-500">
          <p className="text-lg font-medium mb-2">No trades yet</p>
          <p className="text-sm">
            Import your first trades from the{" "}
            <a href="/dashboard/import" className="text-blue-400 hover:underline">
              Import
            </a>{" "}
            page.
          </p>
        </div>
      )}
    </div>
  );
}
