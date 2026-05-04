/**
 * React Query hooks for Reporting Hub analytics data.
 *
 * Provides hooks for:
 *  - Analytics summary (metrics + equity curve + drawdown from server)
 *  - Market phase correlation / attribution
 *  - Equity curve (standalone endpoint)
 *  - Drawdown curve (standalone endpoint)
 *  - Return distribution
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import {
  getAnalyticsSummaryApiV1PortfoliosPortfolioIdAnalyticsSummaryPost,
  getMarketPhaseCorrelationApiV1PortfoliosPortfolioIdAnalyticsCorrelationsMarketPhaseGet,
  getReturnDistributionApiV1PortfoliosPortfolioIdTimeseriesReturnDistributionGet,
} from "@/lib/api";
import type {
  AnalyticsSummary,
  AnalyticsSummaryRequest,
  AttributionResponse,
  DashboardFilterConfig,
} from "@/lib/api/types.gen";
import type {
  EquityCurvePoint,
  DrawdownPoint,
  ReturnDistribution,
} from "@/lib/types";
import type { ScatterPoint } from "@/components/reporting/Widgets";

// ─── Analytics Summary ────────────────────────────────────────────────────────

/**
 * Fetch the analytics summary (metrics, equity curve, drawdown) for a
 * portfolio with optional filter configuration.
 */
export function useAnalyticsSummary(
  portfolioId: string | null,
  filterConfig: DashboardFilterConfig | null,
  viewId?: string | null,
) {
  return useQuery<AnalyticsSummary, Error>({
    queryKey: [
      "analytics-summary",
      portfolioId,
      filterConfig ? JSON.stringify(filterConfig) : null,
      viewId ?? null,
    ],
    queryFn: async () => {
      if (!portfolioId) throw new Error("No portfolio selected");

      const body: AnalyticsSummaryRequest = {};
      if (viewId) {
        body.view_id = viewId;
      } else {
        body.filter_config = filterConfig || {};
      }

      const { data, error } =
        await getAnalyticsSummaryApiV1PortfoliosPortfolioIdAnalyticsSummaryPost({
          path: { portfolio_id: portfolioId },
          body,
        });

      if (error || !data) {
        throw error ?? new Error("Request failed: no data returned");
      }
      return data.data;
    },
    staleTime: 60 * 1000,
    enabled: !!portfolioId,
  });
}

// ─── Market Phase Correlation ─────────────────────────────────────────────────

/**
 * Fetch market phase correlation / attribution data for a portfolio.
 */
export function useMarketPhaseCorrelation(
  portfolioId: string | null,
  filterConfig: DashboardFilterConfig | null,
  viewId?: string | null,
) {
  return useQuery<AttributionResponse, Error>({
    queryKey: [
      "market-phase-correlation",
      portfolioId,
      filterConfig ? JSON.stringify(filterConfig) : null,
      viewId ?? null,
    ],
    queryFn: async () => {
      if (!portfolioId) throw new Error("No portfolio selected");

      const { data, error } =
        await getMarketPhaseCorrelationApiV1PortfoliosPortfolioIdAnalyticsCorrelationsMarketPhaseGet({
          path: { portfolio_id: portfolioId },
          query: {
            from_date: viewId ? undefined : (filterConfig?.date_from ?? undefined),
            to_date: viewId ? undefined : (filterConfig?.date_to ?? undefined),
            view_id: viewId ?? undefined,
          },
        });

      if (error || !data) {
        throw error ?? new Error("Request failed: no data returned");
      }
      return data.data;
    },
    staleTime: 60 * 1000,
    enabled: !!portfolioId,
  });
}

// ─── Equity Curve (standalone) ────────────────────────────────────────────────

// ─── Return Distribution ──────────────────────────────────────────────────────

/**
 * Fetch the return distribution histogram for a portfolio.
 */
export function useReturnDistribution(
  portfolioId: string | null,
  filterConfig: DashboardFilterConfig | null,
) {
  return useQuery<ReturnDistribution[], Error>({
    queryKey: [
      "return-distribution",
      portfolioId,
      filterConfig ? JSON.stringify(filterConfig) : null,
    ],
    queryFn: async () => {
      if (!portfolioId) throw new Error("No portfolio selected");

      const { data, error } =
        await getReturnDistributionApiV1PortfoliosPortfolioIdTimeseriesReturnDistributionGet({
          path: { portfolio_id: portfolioId },
          query: {
            from_dt: filterConfig?.date_from ? `${filterConfig.date_from}T00:00:00Z` : undefined,
            to_dt: filterConfig?.date_to ? `${filterConfig.date_to}T23:59:59Z` : undefined,
          },
        });

      if (error || !data) {
        throw error ?? new Error("Request failed: no data returned");
      }
      return data.data;
    },
    staleTime: 5 * 60 * 1000,
    enabled: !!portfolioId,
  });
}

// ─── Scatter Analytics (Execution Analysis) ────────────────────────────────────

/**
 * Seeded pseudo-random number generator (mulberry32).
 * Produces deterministic values from a numeric seed.
 */
function mulberry32(seed: number): () => number {
  return () => {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function hashPortfolioId(portfolioId: string): number {
  let h = 0;
  for (let i = 0; i < portfolioId.length; i++) {
    h = (Math.imul(31, h) + portfolioId.charCodeAt(i)) | 0;
  }
  return h;
}

function generateMaeMfeMock(seed: number): ScatterPoint[] {
  const rng = mulberry32(seed);
  const points: { x: number; y: number }[] = [];

  for (let i = 0; i < 120; i++) {
    const x = rng() * 2000 + rng() * rng() * 3000;
    const y = rng() * 2500 + rng() * rng() * 4000;
    points.push({ x, y });
  }

  return hexbin(points, 120, 0, 6000, 30, 0, 7000, 40);
}

function generateDurationVsPnlMock(seed: number): ScatterPoint[] {
  const rng = mulberry32(seed);
  const points: { x: number; y: number }[] = [];

  for (let i = 0; i < 100; i++) {
    const x = rng() * 48 + rng() * rng() * 72;
    const y = (rng() - 0.5) * 3000 + (rng() - 0.5) * 5000;
    points.push({ x, y });
  }

  return hexbin(points, 100, 0, 120, 24, -5500, 5500, 40);
}

function hexbin(
  raw: { x: number; y: number }[],
  totalCount: number,
  xMin: number,
  xMax: number,
  xBins: number,
  yMin: number,
  yMax: number,
  yBins: number,
): ScatterPoint[] {
  const xStep = (xMax - xMin) / xBins;
  const yStep = (yMax - yMin) / yBins;
  const bins = new Map<string, number>();

  for (const p of raw) {
    const bx = Math.min(Math.floor((p.x - xMin) / xStep), xBins - 1);
    const by = Math.min(Math.floor((p.y - yMin) / yStep), yBins - 1);
    const key = `${bx}:${by}`;
    bins.set(key, (bins.get(key) ?? 0) + 1);
  }

  const result: ScatterPoint[] = [];
  for (const [key, count] of bins) {
    const [bx, by] = key.split(":").map(Number);
    result.push({
      x: xMin + (bx + 0.5) * xStep,
      y: yMin + (by + 0.5) * yStep,
      count,
      label: `${count} trade${count !== 1 ? "s" : ""}`,
    });
  }

  return result;
}

export interface ScatterAnalyticsResult {
  maeMfe: ScatterPoint[];
  durationVsPnl: ScatterPoint[];
}

/**
 * Fetch execution analysis scatter data (MAE/MFE and Duration vs P&L).
 *
 * Currently uses mock data generation. Will be replaced with a real API
 * call when the backend hexbinning endpoint is available.
 */
export function useScatterAnalytics(
  portfolioId: string | null,
  filterConfig: DashboardFilterConfig | null,
) {
  return useQuery<ScatterAnalyticsResult, Error>({
    queryKey: [
      "scatter-analytics",
      portfolioId,
      filterConfig ? JSON.stringify(filterConfig) : null,
    ],
    queryFn: async () => {
      if (!portfolioId) throw new Error("No portfolio selected");

      const seed = hashPortfolioId(portfolioId);
      return {
        maeMfe: generateMaeMfeMock(seed + 1),
        durationVsPnl: generateDurationVsPnlMock(seed + 2),
      };
    },
    staleTime: 5 * 60 * 1000,
    enabled: !!portfolioId,
  });
}