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
import { useAnalyticsSummary } from "@/hooks/useReportingAnalytics";
import { MetricCard, PayoffRatio, UncategorizedBanner } from "@/components/reporting/Widgets";
import { MetricsSkeleton } from "@/components/reporting/ReportingSkeletons";
import dynamic from "next/dynamic";

const EquityCurveWidget = dynamic(() => import("@/components/reporting/Widgets").then(mod => mod.EquityCurveWidget), { ssr: false });
const DrawdownWidget = dynamic(() => import("@/components/reporting/Widgets").then(mod => mod.DrawdownWidget), { ssr: false });

export default function OverviewPage() {
  const { filter } = useWorkspaceFilter();
  const portfolioId = useActivePortfolioId();
  const { data: summary, isLoading, isError } = useAnalyticsSummary(portfolioId, filter, filter.viewId);

  if (isError) {
    return (
      <div className="p-6">
        <div className="bg-destructive/10 text-destructive px-4 py-3 rounded-md text-sm">
          Failed to load overview data.
        </div>
      </div>
    );
  }

  const equityData = summary?.equity_curve?.map((p) => ({
    date: p.date,
    equity: parseFloat(p.equity),
  }));

  const drawdownData = summary?.drawdown_curve?.map((p) => ({
    date: p.date,
    drawdown: parseFloat(p.drawdown_pct),
  }));

  return (
    <div className="p-6 space-y-6">
      {isLoading && !summary ? (
          <MetricsSkeleton />
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
            <MetricCard
              label="Win Rate"
              value={summary ? formatPercent(summary.win_rate) : "—"}
              sublabel={summary ? `${summary.winning_trades}W / ${summary.losing_trades}L` : undefined}
              trend={summary && parseFloat(summary.win_rate) >= 0.5 ? "up" : "down"}
              helpAnchor="win-rate"
            />
            <MetricCard
              label="Profit Factor"
              value={summary?.profit_factor ? parseFloat(summary.profit_factor).toFixed(2) : "—"}
              trend={summary?.profit_factor && parseFloat(summary.profit_factor) >= 1.5 ? "up" : "down"}
              helpAnchor="profit-factor"
            />
            <PayoffRatio avgWin={summary?.avg_win} avgLoss={summary?.avg_loss} />
            <MetricCard
              label="Total P&L"
              value={summary ? formatCurrency(summary.total_pnl) : "—"}
              trend={summary?.total_pnl && parseFloat(summary.total_pnl) > 0 ? "up" : "down"}
              helpAnchor="net-pnl"
            />
            <MetricCard
              label="Sharpe Ratio"
              value={summary?.sharpe_ratio ? parseFloat(summary.sharpe_ratio).toFixed(2) : "—"}
              trend={summary?.sharpe_ratio && parseFloat(summary.sharpe_ratio) >= 1 ? "up" : "down"}
              helpAnchor="sharpe-ratio"
            />
            <MetricCard
              label="Total Trades"
              value={summary?.total_trades?.toLocaleString("en-US") ?? "—"}
            />
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <EquityCurveWidget data={equityData} isLoading={isLoading} />
          <DrawdownWidget data={drawdownData} isLoading={isLoading} />
        </div>
    </div>
  );
}

function formatPercent(val: string | null | undefined) {
  if (val == null) return "—";
  const num = parseFloat(val);
  return isNaN(num) ? "—" : `${(num * 100).toFixed(1)}%`;
}

function formatCurrency(val: string | null | undefined) {
  if (val == null) return "—";
  const num = parseFloat(val);
  return isNaN(num) ? "—" : new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 }).format(num);
}
