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

import { PageHeader } from "@/components/ui/PageHeader";
import { Spinner } from "@/components/ui/Spinner";
import { useMonthlyPnl } from "@/hooks/useMonthlyPnl";
import { usePnlByAssetClass } from "@/hooks/usePnlByAssetClass";
import { usePnlBySymbol } from "@/hooks/usePnlBySymbol";
import { MonthlyPnlChart } from "@/components/charts/MonthlyPnlChart";
import { PnlByAssetClassChart } from "@/components/charts/PnlByAssetClassChart";
import { PnlBySymbolChart } from "@/components/charts/PnlBySymbolChart";
import { MonthlyWinrateChart } from "@/components/charts/MonthlyWinrateChart";

function ChartSkeleton() {
  return (
    <div className="solid-card p-5 flex items-center justify-center h-48">
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
          <MonthlyWinrateChart />
        </div>
      </div>
    </div>
  );
}
