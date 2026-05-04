/**
 * Dashboard overview page — Radiant / Obsidian deep-dark SaaS layout.
 *
 * Layout order:
 *   1. DashboardHeader  — hero PnL + equity mini-chart
 *   2. DashboardStats   — bento-grid metrics tiles
 *   3. Charts           — equity curve, drawdown, daily PnL, return distribution
 */

"use client";

import { useActivePortfolio } from "@/hooks/useActivePortfolio";
import { useMetrics } from "@/hooks/useMetrics";
import { useDailyPnl } from "@/hooks/useDailyPnl";
import { useReturnDistribution } from "@/hooks/useReturnDistribution";
import { DashboardHeader } from "@/components/dashboard/DashboardHeader";
import { DashboardStats } from "@/components/dashboard/DashboardStats";
import { EquityCurveChart } from "@/components/charts/EquityCurveChart";
import { DrawdownChart } from "@/components/charts/DrawdownChart";
import { DailyPnlBarChart } from "@/components/charts/DailyPnlBarChart";
import { ReturnDistributionChart } from "@/components/charts/ReturnDistributionChart";
import { Spinner } from "@/components/ui/Spinner";

function ChartSkeleton() {
  return (
    <div className="bg-card rounded-xl border border-border overflow-hidden flex items-center justify-center h-48">
      <Spinner />
    </div>
  );
}

export default function DashboardPage() {
  const { activePortfolioId } = useActivePortfolio();
  const { data: summary, isLoading, isError, error, refetch } = useMetrics(activePortfolioId ?? undefined);
  const { data: dailyPnl, isLoading: loadingDaily } = useDailyPnl(activePortfolioId ?? undefined);
  const { data: returnDist, isLoading: loadingReturnDist } = useReturnDistribution(activePortfolioId ?? undefined);

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
        <p className="text-danger font-medium mb-2">Failed to load metrics.</p>
        <p className="text-muted-foreground text-sm mb-4">{error.message}</p>
        <button
          onClick={() => refetch()}
          className="btn-primary text-sm"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!summary) {
    return (
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
    );
  }

  return (
    <div className="space-y-6">
      {/* 1 — Hero */}
      <DashboardHeader summary={summary} />

      {/* 2 — Bento stats grid */}
      <DashboardStats summary={summary} />

      {/* 3 — Charts */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <EquityCurveChart data={summary.equity_curve} />
        <DrawdownChart data={summary.drawdown_curve} />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {loadingDaily ? <ChartSkeleton /> : <DailyPnlBarChart data={dailyPnl ?? []} />}
        {loadingReturnDist ? <ChartSkeleton /> : <ReturnDistributionChart data={returnDist ?? []} />}
      </div>
    </div>
  );
}
