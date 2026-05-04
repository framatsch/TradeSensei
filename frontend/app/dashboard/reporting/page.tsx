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

import { useEffect, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useReportingFilterStore } from "@/stores/reportingFilterStore";
import { usePortfolioStore } from "@/stores/portfolioStore";
import { useDebounce } from "@/hooks/useDebounce";
import {
  useAnalyticsSummary,
  useMarketPhaseCorrelation,
  useReturnDistribution,
  useScatterAnalytics,
} from "@/hooks/useReportingAnalytics";
import { ReportFilterBar } from "@/components/reporting/ReportFilterBar";
import { WidgetGridSkeleton, MetricsSkeleton } from "@/components/reporting/ReportingSkeletons";
import { GlobalEmptyState } from "@/components/reporting/Widgets";
import dynamic from "next/dynamic";
import {
  MetricCard,
  PayoffRatio,
  UncategorizedBanner,
} from "@/components/reporting/Widgets";

// Lazy-load heavy Recharts widgets to prevent main-thread blocking during initial render
const EquityCurveWidget = dynamic(() => import("@/components/reporting/Widgets").then(mod => mod.EquityCurveWidget), { ssr: false });
const DrawdownWidget = dynamic(() => import("@/components/reporting/Widgets").then(mod => mod.DrawdownWidget), { ssr: false });
const RMultipleDistributionWidget = dynamic(() => import("@/components/reporting/Widgets").then(mod => mod.RMultipleDistributionWidget), { ssr: false });
const MaeMfeScatterWidget = dynamic(() => import("@/components/reporting/Widgets").then(mod => mod.MaeMfeScatterWidget), { ssr: false });
const DurationVsPnlScatterWidget = dynamic(() => import("@/components/reporting/Widgets").then(mod => mod.DurationVsPnlScatterWidget), { ssr: false });
const PlaybookPhaseHeatmapWidget = dynamic(() => import("@/components/reporting/Widgets").then(mod => mod.PlaybookPhaseHeatmapWidget), { ssr: false });
const PsychologicalAttributionWidget = dynamic(() => import("@/components/reporting/Widgets").then(mod => mod.PsychologicalAttributionWidget), { ssr: false });

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

  const { data: returnDistribution, isLoading: distributionLoading } =
    useReturnDistribution(portfolioId, filterConfig);

  const {
    data: scatterData,
    isLoading: scatterLoading,
  } = useScatterAnalytics(portfolioId, filterConfig);

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

  const equityCurveData = useMemo(() => {
    return summary?.equity_curve?.map((p) => ({
      date: p.date,
      equity: parseFloat(p.equity),
    }));
  }, [summary?.equity_curve]);

  const drawdownCurveData = useMemo(() => {
    return summary?.drawdown_curve?.map((p) => ({
      date: p.date,
      drawdown: parseFloat(p.drawdown_pct),
    }));
  }, [summary?.drawdown_curve]);

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
              data={equityCurveData}
              isLoading={summaryLoading}
            />
            <DrawdownWidget
              data={drawdownCurveData}
              isLoading={summaryLoading}
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
            <MaeMfeScatterWidget
              data={scatterData?.maeMfe}
              isLoading={scatterLoading}
            />
            <DurationVsPnlScatterWidget
              data={scatterData?.durationVsPnl}
              isLoading={scatterLoading}
            />
          </div>
        </div>
      )}
    </div>
  );
}
