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

import React, { useState, useMemo } from "react";
import { useWorkspaceFilter, useActivePortfolioId } from "@/components/workspace/WorkspaceFilterContext";
import { useGetAnnotationDefinitions } from "@/hooks/useAnnotationDefinitions";
import { useGetTaxonomies } from "@/hooks/useTaxonomies";
import { useMetadataCorrelation } from "@/hooks/useMetadataCorrelation";
import { CorrelationChartRouter } from "@/components/charts/CorrelationChartRouter";
import { useAccounts } from "@/hooks/useAccounts";
import { MetricHelpLink } from "@/components/ui/MetricHelpLink";

const INPUT_CLASS =
  "w-full px-3 py-2 bg-secondary border border-border rounded-md text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary";

const LABEL_CLASS = "block text-xs font-medium text-muted-foreground mb-1";

export default function CorrelationPage() {
  const { filter, setFilter } = useWorkspaceFilter();
  const portfolioId = useActivePortfolioId();

  // Filter state
  const dateFrom = filter.date_from ?? "";
  const dateTo = filter.date_to ?? "";
  const accountIds = filter.account_ids || [];

  // Local state
  const [baseAsset, setBaseAsset] = useState<string>("");
  const [xAxisRaw, setXAxisRaw] = useState<string>("");
  const [yAxisRaw, setYAxisRaw] = useState<string>("");

  const { data: accounts } = useAccounts(portfolioId ?? undefined);

  const { data: annotationDefs } = useGetAnnotationDefinitions(undefined);
  const { data: taxonomyDefs } = useGetTaxonomies(undefined);

  // Parse selected axes
  const xParts = xAxisRaw.split("|");
  const xType = xParts[0] as any;
  const xId = xParts[1] || "";

  const yParts = yAxisRaw.split("|");
  const yType = yParts[0] as any;
  const yId = yParts[1] || "";

  const hasAxes = !!(xId && yId);

  const { data: correlationData, isLoading, isError } = useMetadataCorrelation({
    portfolioId: portfolioId || "",
    x_axis_type: xType,
    x_axis_id: xId,
    y_axis_type: yType,
    y_axis_id: yId,
    filter_config: filter,
    view_id: filter.viewId || undefined,
    base_asset: baseAsset || undefined,
  });

  const chartDataPoints = useMemo(() => {
    if (!correlationData?.data_points) return [];
    return correlationData.data_points.map(dp => ({
      x: dp.x_value ?? dp.x_label ?? "",
      y: dp.y_value ?? dp.y_label ?? "",
    }));
  }, [correlationData]);

  // Group definitions for selects
  // Group definitions for selects — use token-based scope matching
  const tradeAnnotations = annotationDefs?.filter(d => d.scope.split(",").some(t => t.trim() === "trades")) || [];
  const checkinAnnotations = annotationDefs?.filter(d => d.scope.split(",").some(t => t.trim() === "checkins")) || [];
  const tradeTaxonomies = taxonomyDefs?.filter(d => d.scope.split(",").some(t => t.trim() === "trades")) || [];
  const checkinTaxonomies = taxonomyDefs?.filter(d => d.scope.split(",").some(t => t.trim() === "checkins")) || [];

  const renderAxisOptions = () => (
    <>
      <option value="" disabled>Select Axis...</option>
      <optgroup label="Check-in Annotations">
        {checkinAnnotations.map(a => <option key={`checkin_annotation|${a.id}`} value={`checkin_annotation|${a.id}`}>{a.name}</option>)}
      </optgroup>
      <optgroup label="Trade Annotations">
        {tradeAnnotations.map(a => <option key={`trade_annotation|${a.id}`} value={`trade_annotation|${a.id}`}>{a.name}</option>)}
      </optgroup>
      <optgroup label="Check-in Taxonomies">
        {checkinTaxonomies.map(t => <option key={`checkin_taxonomy|${t.id}`} value={`checkin_taxonomy|${t.id}`}>{t.name}</option>)}
      </optgroup>
      <optgroup label="Trade Taxonomies">
        {tradeTaxonomies.map(t => <option key={`trade_taxonomy|${t.id}`} value={`trade_taxonomy|${t.id}`}>{t.name}</option>)}
      </optgroup>
    </>
  );

  const kpis = correlationData?.kpis;

  return (
    <div className="p-6 space-y-6 pt-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Metadata Correlation</h1>
      </div>

      {/* Filter Bar */}
      <div className="w-full solid-card shadow-sm p-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <label className={LABEL_CLASS}>Date From</label>
            <input
              type="date"
              aria-label="Date From"
              value={dateFrom}
              onChange={(e) => setFilter(prev => ({ ...prev, date_from: e.target.value || null }))}
              className={INPUT_CLASS}
            />
          </div>
          <div>
            <label className={LABEL_CLASS}>Date To</label>
            <input
              type="date"
              aria-label="Date To"
              value={dateTo}
              onChange={(e) => setFilter(prev => ({ ...prev, date_to: e.target.value || null }))}
              className={INPUT_CLASS}
            />
          </div>
          <div>
            <label className={LABEL_CLASS}>Account</label>
            <select
              aria-label="Account"
              value={accountIds.length === 1 ? accountIds[0] : ""}
              onChange={(e) => setFilter(prev => ({ ...prev, account_ids: e.target.value ? [e.target.value] : [] }))}
              className={INPUT_CLASS}
            >
              <option value="">All Accounts</option>
              {accounts?.map(acc => (
                <option key={acc.id} value={acc.id}>{acc.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className={LABEL_CLASS}>Base Asset</label>
            <input
              type="text"
              aria-label="Base Asset"
              placeholder="e.g. AAPL"
              value={baseAsset}
              onChange={(e) => setBaseAsset(e.target.value)}
              className={INPUT_CLASS}
            />
          </div>
        </div>
      </div>

      {/* Axes Selection */}
      <div className="w-full solid-card shadow-sm p-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className={LABEL_CLASS}>X-Axis</label>
            <select
              aria-label="X-Axis Selector"
              value={xAxisRaw}
              onChange={(e) => setXAxisRaw(e.target.value)}
              className={INPUT_CLASS}
            >
              {renderAxisOptions()}
            </select>
          </div>
          <div>
            <label className={LABEL_CLASS}>Y-Axis</label>
            <select
              aria-label="Y-Axis Selector"
              value={yAxisRaw}
              onChange={(e) => setYAxisRaw(e.target.value)}
              className={INPUT_CLASS}
            >
              {renderAxisOptions()}
            </select>
          </div>
        </div>
      </div>

      {isError && (
        <div className="bg-destructive/10 text-destructive px-4 py-3 rounded-md text-sm">
          Failed to load correlation data.
        </div>
      )}

      {/* KPIs */}
      {hasAxes && !isError && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="solid-card p-4">
            <div className="text-sm font-medium text-muted-foreground flex items-center justify-between">
              <span>Win Rate</span>
              <MetricHelpLink anchor="win-rate" />
            </div>
            <div className="text-2xl font-bold font-mono mt-1">
              {kpis?.win_rate ? `${(Number(kpis.win_rate) * 100).toFixed(1)}%` : "—"}
            </div>
          </div>
          <div className="solid-card p-4">
            <div className="text-sm font-medium text-muted-foreground flex items-center justify-between">
              <span>Max Drawdown</span>
              <MetricHelpLink anchor="max-drawdown" />
            </div>
            <div className="text-2xl font-bold font-mono mt-1 text-danger">
              {kpis?.max_drawdown_pct ? `${(Number(kpis.max_drawdown_pct) * 100).toFixed(1)}%` : "—"}
            </div>
          </div>
          <div className="solid-card p-4">
            <div className="text-sm font-medium text-muted-foreground">Matched / Total</div>
            <div className="text-2xl font-bold font-mono mt-1">
              {kpis ? `${kpis.matched_count} / ${kpis.total_trades_count}` : "—"}
            </div>
          </div>
        </div>
      )}

      {/* Chart */}
      {hasAxes && !isError && (
        <div className="h-[400px] w-full solid-card shadow-sm p-4">
          {isLoading ? (
            <div className="flex h-full items-center justify-center text-sm text-muted-foreground">Loading chart...</div>
          ) : correlationData ? (
            <CorrelationChartRouter
              x_axis_data_type={correlationData.x_axis_data_type as "continuous" | "categorical"}
              y_axis_data_type={correlationData.y_axis_data_type as "continuous" | "categorical"}
              data_points={chartDataPoints}
              xAxisLabel={xAxisRaw.split("|")[1] ? (annotationDefs?.find(d => d.id === xId) || taxonomyDefs?.find(t => t.id === xId))?.name : "X Axis"}
              yAxisLabel={yAxisRaw.split("|")[1] ? (annotationDefs?.find(d => d.id === yId) || taxonomyDefs?.find(t => t.id === yId))?.name : "Y Axis"}
            />
          ) : null}
        </div>
      )}

      {/* Raw Data Table */}
      {hasAxes && correlationData?.data_points && correlationData.data_points.length > 0 && (
        <div className="w-full solid-card shadow-sm overflow-hidden">
          <div className="p-4 border-b border-border">
            <h2 className="text-lg font-semibold">Raw Data</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="radiant-table w-full text-sm">
              <thead className="bg-secondary/50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">Date</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">Symbol</th>
                  <th className="px-4 py-2 text-right font-medium text-muted-foreground">P&L</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">X Value</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">Y Value</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {correlationData.data_points.map((dp, idx) => (
                  <tr key={`${dp.trade_id}-${idx}`} className="hover:bg-muted/50 transition-colors">
                    <td className="px-4 py-2 whitespace-nowrap">{new Date(dp.date).toLocaleDateString()}</td>
                    <td className="px-4 py-2 font-mono whitespace-nowrap">{dp.trade_symbol}</td>
                    <td className={`px-4 py-2 text-right font-mono whitespace-nowrap ${Number(dp.trade_pnl) >= 0 ? "text-success" : "text-danger"}`}>
                      ${Number(dp.trade_pnl).toFixed(2)}
                    </td>
                    <td className="px-4 py-2 whitespace-nowrap">{dp.x_label ?? dp.x_value ?? "—"}</td>
                    <td className="px-4 py-2 whitespace-nowrap">{dp.y_label ?? dp.y_value ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
