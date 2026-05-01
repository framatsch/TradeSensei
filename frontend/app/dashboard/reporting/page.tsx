/**
 * Reporting Hub — analytics dashboard with view management, global filters,
 * and a reactive widget grid of charts and metrics.
 *
 * URL-based state: filter params are stored in URL search params so views
 * can be bookmarked and shared.
 *
 * Layout:
 *  1. View Management bar (saved views dropdown + save/delete actions)
 *  2. Global Filters Panel (collapsible ReportFilterBar)
 *  3. Widget Grid (metrics cards + charts)
 */

"use client";

import { useEffect, useCallback, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useReportingFilterStore } from "@/stores/reportingFilterStore";
import { usePortfolioStore } from "@/stores/portfolioStore";
import { useDebounce } from "@/hooks/useDebounce";
import {
  useAnalyticsSummary,
  useMarketPhaseCorrelation,
  useEquityCurve,
  useDrawdownCurve,
  useReturnDistribution,
} from "@/hooks/useReportingAnalytics";
import { useSavedViews, useSaveView, useDeleteView } from "@/hooks/useReportingViews";
import { ReportFilterBar } from "@/components/reporting/ReportFilterBar";
import { WidgetGridSkeleton, MetricsSkeleton } from "@/components/reporting/ReportingSkeletons";
import { GlobalEmptyState } from "@/components/reporting/Widgets";
import {
  MetricCard,
  PayoffRatio,
  EquityCurveWidget,
  DrawdownWidget,
  RMultipleDistributionWidget,
  MaeMfeScatterWidget,
  DurationVsPnlScatterWidget,
  PlaybookPhaseHeatmapWidget,
  PsychologicalAttributionWidget,
  UncategorizedBanner,
} from "@/components/reporting/Widgets";
import type {
  HeatmapCell,
  AttributionBar,
  EquityCurvePoint,
  DrawdownPoint,
  RMultipleBucket,
} from "@/components/reporting/Widgets";
import type {
  DashboardFilterConfig,
  MarketPhaseCorrelation,
} from "@/lib/api/types.gen";
import { Save, Trash2 } from "lucide-react";

// ─── URL param keys ───────────────────────────────────────────────────────────

const PARAM_KEYS = {
  viewId: "view_id",
  dateFrom: "date_from",
  dateTo: "date_to",
  playbookIds: "playbook_ids",
  tagIds: "tag_ids",
  includeOpen: "include_open",
} as const;

// ─── Helpers ──────────────────────────────────────────────────────────────────

function buildFilterConfig(
  dateFrom: string | null,
  dateTo: string | null,
  playbookIds: string[],
  tagIds: string[],
): DashboardFilterConfig {
  const config: DashboardFilterConfig = {};
  if (dateFrom) config.date_from = dateFrom;
  if (dateTo) config.date_to = dateTo;
  if (playbookIds.length > 0) config.playbook_ids = playbookIds;
  if (tagIds.length > 0) config.tag_ids = tagIds;
  return config;
}

function formatPercent(value: string | null | undefined): string {
  if (value == null) return "—";
  const num = parseFloat(value);
  if (isNaN(num)) return "—";
  return (num * 100).toFixed(1) + "%";
}

function formatCurrency(value: string | null | undefined): string {
  if (value == null) return "—";
  const num = parseFloat(value);
  if (isNaN(num)) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(num);
}

function formatNumber(value: number | null | undefined): string {
  if (value == null) return "—";
  return value.toLocaleString("en-US");
}

// ─── Data transformers ────────────────────────────────────────────────────────

function toHeatmapCells(
  buckets: MarketPhaseCorrelation[] | undefined,
): HeatmapCell[] {
  if (!buckets) return [];
  return buckets.map((b) => ({
    playbook: b.label ?? "Unknown",
    phase: b.market_phase ?? "Unset",
    trade_count: b.trade_count,
    win_rate: b.win_rate,
    avg_pnl: b.avg_pnl ?? "0",
  }));
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
      label: "No Check-in",
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

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function ReportingHubPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // ── Store state ──────────────────────────────────────────────────────────
  const {
    portfolioId,
    dateFrom,
    dateTo,
    playbookIds,
    tagIds,
    includeOpenTrades,
    viewId,
    setPortfolioId,
    setDateFrom,
    setDateTo,
    setPlaybookIds,
    setTagIds,
    setIncludeOpenTrades,
    setViewId,
    setFilters,
  } = useReportingFilterStore();

  const activePortfolioId = usePortfolioStore((s) => s.activePortfolioId);

  // ── Hydrate portfolio from portfolioStore on mount ───────────────────────
  useEffect(() => {
    if (activePortfolioId && !portfolioId) {
      setPortfolioId(activePortfolioId);
    }
  }, [activePortfolioId, portfolioId, setPortfolioId]);

  // ── Hydrate filters from URL on mount ────────────────────────────────────
  useEffect(() => {
    const urlViewId = searchParams.get(PARAM_KEYS.viewId);
    const urlDateFrom = searchParams.get(PARAM_KEYS.dateFrom);
    const urlDateTo = searchParams.get(PARAM_KEYS.dateTo);
    const urlPlaybookIds = searchParams.get(PARAM_KEYS.playbookIds);
    const urlTagIds = searchParams.get(PARAM_KEYS.tagIds);
    const urlIncludeOpen = searchParams.get(PARAM_KEYS.includeOpen);

    setFilters({
      viewId: urlViewId || null,
      dateFrom: urlDateFrom || null,
      dateTo: urlDateTo || null,
      playbookIds: urlPlaybookIds ? urlPlaybookIds.split(",").filter(Boolean) : [],
      tagIds: urlTagIds ? urlTagIds.split(",").filter(Boolean) : [],
      includeOpenTrades: urlIncludeOpen === "true",
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Sync store → URL (debounced) ─────────────────────────────────────────
  const debouncedFilters = useDebounce(
    { dateFrom, dateTo, playbookIds, tagIds, includeOpenTrades, viewId },
    400,
  );

  useEffect(() => {
    const params = new URLSearchParams();

    if (debouncedFilters.viewId) params.set(PARAM_KEYS.viewId, debouncedFilters.viewId);
    if (debouncedFilters.dateFrom) params.set(PARAM_KEYS.dateFrom, debouncedFilters.dateFrom);
    if (debouncedFilters.dateTo) params.set(PARAM_KEYS.dateTo, debouncedFilters.dateTo);
    if (debouncedFilters.playbookIds.length > 0)
      params.set(PARAM_KEYS.playbookIds, debouncedFilters.playbookIds.join(","));
    if (debouncedFilters.tagIds.length > 0)
      params.set(PARAM_KEYS.tagIds, debouncedFilters.tagIds.join(","));
    if (debouncedFilters.includeOpenTrades)
      params.set(PARAM_KEYS.includeOpen, "true");

    const queryString = params.toString();
    const newUrl = queryString
      ? `/dashboard/reporting?${queryString}`
      : "/dashboard/reporting";

    router.replace(newUrl, { scroll: false });
  }, [debouncedFilters, router]);

  // ── Build filter config for API calls ────────────────────────────────────
  const filterConfig = useMemo(
    () => buildFilterConfig(dateFrom, dateTo, playbookIds, tagIds),
    [dateFrom, dateTo, playbookIds, tagIds],
  );

  // ── Data fetching ────────────────────────────────────────────────────────
  const {
    data: summary,
    isLoading: summaryLoading,
    isError: summaryError,
  } = useAnalyticsSummary(portfolioId, filterConfig, viewId);

  const {
    data: attribution,
    isLoading: attributionLoading,
  } = useMarketPhaseCorrelation(portfolioId, filterConfig, viewId);

  const { data: equityCurve, isLoading: equityLoading } =
    useEquityCurve(portfolioId);

  const { data: drawdownCurve, isLoading: drawdownLoading } =
    useDrawdownCurve(portfolioId);

  const { data: returnDistribution, isLoading: distributionLoading } =
    useReturnDistribution(portfolioId);

  // ── Derived data ─────────────────────────────────────────────────────────
  const heatmapCells = useMemo(
    () => toHeatmapCells(attribution?.buckets),
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

  const rMultipleData: RMultipleBucket[] | undefined = useMemo(
    () =>
      returnDistribution?.map((d) => ({
        bucket_min: String(d.bucket_min),
        bucket_max: String(d.bucket_max),
        count: d.count,
      })),
    [returnDistribution],
  );

  const isInitialLoad =
    summaryLoading && !summary;

  // ── Saved views ──────────────────────────────────────────────────────────
  const { data: savedViews } = useSavedViews(portfolioId);
  const saveViewMutation = useSaveView(portfolioId);
  const deleteViewMutation = useDeleteView(portfolioId);

  const [saveViewName, setSaveViewName] = useState("");
  const [showSaveInput, setShowSaveInput] = useState(false);

  const handleSaveView = useCallback(() => {
    if (!saveViewName.trim() || !portfolioId) return;
    saveViewMutation.mutate(
      {
        name: saveViewName.trim(),
        filter_config: filterConfig,
      },
      {
        onSuccess: (newView) => {
          setViewId(newView.id);
          setSaveViewName("");
          setShowSaveInput(false);
        },
      },
    );
  }, [saveViewName, portfolioId, filterConfig, saveViewMutation, setViewId]);

  const handleDeleteView = useCallback(
    (id: string) => {
      if (!confirm("Delete this saved view?")) return;
      deleteViewMutation.mutate(id, {
        onSuccess: () => {
          if (viewId === id) {
            setViewId(null);
          }
        },
      });
    },
    [deleteViewMutation, viewId, setViewId],
  );

  const handleViewSelect = useCallback(
    (id: string) => {
      const view = savedViews?.find((v) => v.id === id);
      if (view) {
        setViewId(view.id);
        setFilters({
          dateFrom: view.filter_config.date_from ?? null,
          dateTo: view.filter_config.date_to ?? null,
          playbookIds: view.filter_config.playbook_ids ?? [],
          tagIds: view.filter_config.tag_ids ?? [],
        });
      }
    },
    [savedViews, setViewId, setFilters],
  );

  // ── No portfolio state ───────────────────────────────────────────────────
  if (!portfolioId) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-muted-foreground text-sm">
          Select a portfolio to view analytics.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* ── Page header ──────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">
            Reporting Hub
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Analytics dashboard with saved views and global filters
          </p>
        </div>
      </div>

      {/* ── View Management bar ──────────────────────────────────────────── */}
      <div className="bg-card rounded-xl border border-border p-4">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="relative flex-1 min-w-[200px] max-w-xs">
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Saved View
            </label>
            <select
              value={viewId ?? ""}
              onChange={(e) => {
                if (e.target.value) {
                  handleViewSelect(e.target.value);
                } else {
                  setViewId(null);
                }
              }}
              className="w-full px-3 py-2 bg-secondary border border-border rounded-md text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="">Unsaved view</option>
              {(savedViews ?? []).map((v) => (
                <option key={v.id} value={v.id}>
                  {v.name}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2 pt-5">
            {showSaveInput ? (
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={saveViewName}
                  onChange={(e) => setSaveViewName(e.target.value)}
                  placeholder="View name..."
                  className="w-40 px-3 py-2 bg-secondary border border-border rounded-md text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleSaveView();
                    if (e.key === "Escape") {
                      setShowSaveInput(false);
                      setSaveViewName("");
                    }
                  }}
                  autoFocus
                />
                <button
                  type="button"
                  onClick={handleSaveView}
                  disabled={!saveViewName.trim() || saveViewMutation.isPending}
                  className="px-3 py-2 text-sm rounded-md bg-primary text-primary-foreground hover:opacity-90 transition-opacity disabled:opacity-50"
                >
                  {saveViewMutation.isPending ? "Saving..." : "Save"}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowSaveInput(false);
                    setSaveViewName("");
                  }}
                  className="px-3 py-2 text-sm rounded-md bg-secondary text-muted-foreground hover:text-foreground transition-colors"
                >
                  Cancel
                </button>
              </div>
            ) : (
              <>
                <button
                  type="button"
                  onClick={() => setShowSaveInput(true)}
                  className="inline-flex items-center gap-1.5 px-3 py-2 text-sm rounded-md bg-secondary text-muted-foreground hover:text-foreground transition-colors"
                >
                  <Save className="w-3.5 h-3.5" />
                  Save View
                </button>
                {viewId && (
                  <button
                    type="button"
                    onClick={() => handleDeleteView(viewId)}
                    disabled={deleteViewMutation.isPending}
                    className="inline-flex items-center gap-1.5 px-3 py-2 text-sm rounded-md bg-secondary text-danger hover:bg-destructive/10 transition-colors disabled:opacity-50"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    Delete
                  </button>
                )}
              </>
            )}
          </div>
        </div>
      </div>

      {/* ── Global Filters ───────────────────────────────────────────────── */}
      <ReportFilterBar />

      {/* ── Error state ──────────────────────────────────────────────────── */}
      {summaryError && (
        <div className="bg-destructive/10 text-destructive px-4 py-3 rounded-md text-sm">
          Failed to load analytics data. Please try again.
        </div>
      )}

      {/* ── Loading skeleton ─────────────────────────────────────────────── */}
      {isInitialLoad && <WidgetGridSkeleton />}

      {/* ── Global empty state ───────────────────────────────────────────── */}
      {!isInitialLoad &&
        summary &&
        !summary.total_trades &&
        (!attribution || attribution.buckets.length === 0) && (
          <GlobalEmptyState />
        )}

      {/* ── Widget Grid ──────────────────────────────────────────────────── */}
      {!isInitialLoad && (
        <div className="space-y-6">
          {/* Metrics row: Win Rate, Profit Factor, Payoff Ratio, Total P&L, Sharpe, Total Trades */}
          {summaryLoading && !summary ? (
            <MetricsSkeleton />
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
              <MetricCard
                label="Win Rate"
                value={summary ? formatPercent(summary.win_rate) : "—"}
                sublabel={
                  summary
                    ? `${summary.winning_trades}W / ${summary.losing_trades}L`
                    : undefined
                }
                trend={
                  summary && parseFloat(summary.win_rate) >= 0.5 ? "up" : "down"
                }
              />
              <MetricCard
                label="Profit Factor"
                value={
                  summary?.profit_factor
                    ? parseFloat(summary.profit_factor).toFixed(2)
                    : "—"
                }
                trend={
                  summary?.profit_factor &&
                  parseFloat(summary.profit_factor) >= 1.5
                    ? "up"
                    : "down"
                }
              />
              <PayoffRatio
                avgWin={summary?.avg_win}
                avgLoss={summary?.avg_loss}
              />
              <MetricCard
                label="Total P&L"
                value={summary ? formatCurrency(summary.gross_profit) : "—"}
                trend={
                  summary?.gross_profit && parseFloat(summary.gross_profit) > 0
                    ? "up"
                    : "down"
                }
              />
              <MetricCard
                label="Sharpe Ratio"
                value={
                  summary?.sharpe_ratio
                    ? parseFloat(summary.sharpe_ratio).toFixed(2)
                    : "—"
                }
                trend={
                  summary?.sharpe_ratio &&
                  parseFloat(summary.sharpe_ratio) >= 1.0
                    ? "up"
                    : "down"
                }
              />
              <MetricCard
                label="Total Trades"
                value={summary ? formatNumber(summary.total_trades) : "—"}
              />
            </div>
          )}

          {/* Performance Classic: Equity Curve + Drawdown */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <EquityCurveWidget
              data={equityCurve as EquityCurvePoint[] | undefined}
              isLoading={equityLoading}
            />
            <DrawdownWidget
              data={drawdownCurve as DrawdownPoint[] | undefined}
              isLoading={drawdownLoading}
            />
          </div>

          {/* R-Multiple Distribution + Market Phase Attribution */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <RMultipleDistributionWidget
              data={rMultipleData}
              isLoading={distributionLoading}
            />
            <PsychologicalAttributionWidget
              data={attributionBars}
              isLoading={attributionLoading}
            />
          </div>

          {/* Attribution: Playbook-Phase Heatmap + Uncategorized Banner */}
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

          {/* Execution Analysis: MAE/MFE + Duration vs P&L */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <MaeMfeScatterWidget data={undefined} isLoading={false} />
            <DurationVsPnlScatterWidget data={undefined} isLoading={false} />
          </div>
        </div>
      )}
    </div>
  );
}
