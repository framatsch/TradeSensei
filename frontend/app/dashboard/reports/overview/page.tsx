"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { Spinner } from "@/components/ui/Spinner";
import { useMonthlyPnl } from "@/hooks/useMonthlyPnl";
import { usePnlByAssetClass } from "@/hooks/usePnlByAssetClass";
import { usePnlBySymbol } from "@/hooks/usePnlBySymbol";
import { MonthlyPnlChart } from "@/components/charts/MonthlyPnlChart";
import { PnlByAssetClassChart } from "@/components/charts/PnlByAssetClassChart";
import { PnlBySymbolChart } from "@/components/charts/PnlBySymbolChart";
import { RollingWinrateChart } from "@/components/charts/RollingWinrateChart";
import { MonthlyWinrateChart } from "@/components/charts/MonthlyWinrateChart";

function ChartSkeleton() {
  return (
    <div className="bg-card rounded-xl p-5 border border-border flex items-center justify-center h-48">
      <Spinner />
    </div>
  );
}

export default function OverviewPage() {
  const { data: monthlyPnl, isLoading: loadingMonthly } = useMonthlyPnl();
  const { data: pnlByAssetClass, isLoading: loadingAssetClass } = usePnlByAssetClass();
  const { data: pnlBySymbol, isLoading: loadingBySymbol } = usePnlBySymbol();

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <PageHeader title="Overview" subtitle="High-level performance summary" />

      <div className="space-y-6">
        <div>
          {loadingMonthly ? <ChartSkeleton /> : <MonthlyPnlChart data={monthlyPnl ?? []} />}
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          {loadingAssetClass ? <ChartSkeleton /> : <PnlByAssetClassChart data={pnlByAssetClass ?? []} />}
          {loadingBySymbol ? (
            <ChartSkeleton />
          ) : (
            <PnlBySymbolChart
              data={(pnlBySymbol ?? []).map((d) => ({ symbol: d.symbol, pnl: parseFloat(d.total_pnl) }))}
            />
          )}
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <RollingWinrateChart />
          <MonthlyWinrateChart />
        </div>
      </div>
    </div>
  );
}
