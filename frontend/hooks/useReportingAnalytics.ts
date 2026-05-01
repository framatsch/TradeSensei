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
  getEquityCurveApiV1PortfoliosPortfolioIdMetricsEquityCurveGet,
  getDrawdownCurveApiV1PortfoliosPortfolioIdMetricsDrawdownGet,
  getReturnDistributionApiV1PortfoliosPortfolioIdTimeseriesReturnDistributionGet,
} from "@/lib/api/services.gen";
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
      if (filterConfig) {
        body.filter_config = filterConfig;
      }
      if (viewId) {
        body.view_id = viewId;
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
            from_date: filterConfig?.date_from ?? null,
            to_date: filterConfig?.date_to ?? null,
            view_id: viewId ?? null,
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

/**
 * Fetch the equity curve time series for a portfolio.
 */
export function useEquityCurve(portfolioId: string | null) {
  return useQuery<EquityCurvePoint[], Error>({
    queryKey: ["equity-curve", portfolioId],
    queryFn: async () => {
      if (!portfolioId) throw new Error("No portfolio selected");

      const { data, error } =
        await getEquityCurveApiV1PortfoliosPortfolioIdMetricsEquityCurveGet({
          path: { portfolio_id: portfolioId },
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

// ─── Drawdown Curve (standalone) ──────────────────────────────────────────────

/**
 * Fetch the drawdown curve time series for a portfolio.
 */
export function useDrawdownCurve(portfolioId: string | null) {
  return useQuery<DrawdownPoint[], Error>({
    queryKey: ["drawdown-curve", portfolioId],
    queryFn: async () => {
      if (!portfolioId) throw new Error("No portfolio selected");

      const { data, error } =
        await getDrawdownCurveApiV1PortfoliosPortfolioIdMetricsDrawdownGet({
          path: { portfolio_id: portfolioId },
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

// ─── Return Distribution ──────────────────────────────────────────────────────

/**
 * Fetch the return distribution histogram for a portfolio.
 */
export function useReturnDistribution(portfolioId: string | null) {
  return useQuery<ReturnDistribution[], Error>({
    queryKey: ["return-distribution", portfolioId],
    queryFn: async () => {
      if (!portfolioId) throw new Error("No portfolio selected");

      const { data, error } =
        await getReturnDistributionApiV1PortfoliosPortfolioIdTimeseriesReturnDistributionGet({
          path: { portfolio_id: portfolioId },
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