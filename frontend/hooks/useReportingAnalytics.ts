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
import { useMemo } from "react";
import { useReportData } from "@/hooks/useReportData";
import {
  getAnalyticsSummaryApiV1PortfoliosPortfolioIdAnalyticsSummaryPost,
  getMarketPhaseCorrelationApiV1PortfoliosPortfolioIdAnalyticsCorrelationsMarketPhasePost,
  getAnalyticsReturnDistributionApiV1PortfoliosPortfolioIdAnalyticsReturnDistributionPost,
} from "@/lib/api";
import type {
  AnalyticsSummary,
  AnalyticsSummaryRequest,
  AttributionResponse,
  DashboardFilterConfig,
} from "@/lib/api/types.gen";
import type {
  Trade,
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
    queryFn: async ({ signal }) => {
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
          signal,
        } as any);

      if (error || !data) {
        throw error ?? new Error("Request failed: no data returned");
      }
      return data.data;
    },
    staleTime: 5 * 60 * 1000,
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
    queryFn: async ({ signal }) => {
      if (!portfolioId) throw new Error("No portfolio selected");

      const body: AnalyticsSummaryRequest = {};
      if (viewId) {
        body.view_id = viewId;
      } else {
        body.filter_config = filterConfig || {};
      }

      const { data, error } =
        await getMarketPhaseCorrelationApiV1PortfoliosPortfolioIdAnalyticsCorrelationsMarketPhasePost(
          {
            path: { portfolio_id: portfolioId },
            body,
            signal,
          } as any
        );

      if (error || !data) {
        throw error ?? new Error("Request failed: no data returned");
      }
      return data.data;
    },
    staleTime: 5 * 60 * 1000,
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
  viewId?: string | null,
) {
  return useQuery<ReturnDistribution[], Error>({
    queryKey: [
      "return-distribution",
      portfolioId,
      filterConfig ? JSON.stringify(filterConfig) : null,
      viewId ?? null,
    ],
    queryFn: async ({ signal }) => {
      if (!portfolioId) throw new Error("No portfolio selected");

      const body: AnalyticsSummaryRequest = {};
      if (viewId) {
        body.view_id = viewId;
      } else {
        body.filter_config = filterConfig || {};
      }

      const { data, error } =
        await getAnalyticsReturnDistributionApiV1PortfoliosPortfolioIdAnalyticsReturnDistributionPost(
          {
            path: { portfolio_id: portfolioId },
            body,
            signal,
          } as any
        );

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

function parseTradePnl(trade: Trade): number {
  const raw = trade.net_pnl ?? trade.pnl;
  if (raw == null) return 0;
  const parsed = typeof raw === "string" ? parseFloat(raw) : Number(raw);
  return Number.isFinite(parsed) ? parsed : 0;
}

function generateMaeMfeMock(trades: Trade[], seed: number): ScatterPoint[] {
  const points: { x: number; y: number }[] = [];

  for (const trade of trades) {
    const tradeSeed = hashPortfolioId(`${seed}:${trade.id}`);
    const rng = mulberry32(tradeSeed);
    const pnlMagnitude = Math.abs(parseTradePnl(trade));
    const base = Math.max(25, pnlMagnitude);
    const mae = base * (0.2 + rng() * 0.9);
    const mfe = mae + base * (0.4 + rng() * 1.2);
    points.push({ x: mae, y: mfe });
  }

  if (points.length === 0) return [];
  const maxMae = Math.max(...points.map((p) => p.x), 1000);
  const maxMfe = Math.max(...points.map((p) => p.y), 1000);

  return hexbin(points, 0, 0, maxMae * 1.1, 30, 0, maxMfe * 1.1, 40);
}

function generateDurationVsPnlMock(trades: Trade[]): ScatterPoint[] {
  const points: { x: number; y: number }[] = [];

  for (const trade of trades) {
    if (!trade.closed_at) continue;

    const opened = new Date(trade.opened_at).getTime();
    const closed = new Date(trade.closed_at).getTime();
    if (!Number.isFinite(opened) || !Number.isFinite(closed) || closed < opened) {
      continue;
    }

    const durationHours = (closed - opened) / (1000 * 60 * 60);
    const pnl = parseTradePnl(trade);
    points.push({ x: durationHours, y: pnl });
  }

  if (points.length === 0) return [];
  const maxDuration = Math.max(...points.map((p) => p.x), 24);
  const maxAbsPnl = Math.max(...points.map((p) => Math.abs(p.y)), 100);

  return hexbin(
    points,
    0,
    0,
    maxDuration * 1.1,
    24,
    -maxAbsPnl * 1.1,
    maxAbsPnl * 1.1,
    40,
  );
}

function generateFallbackMaeMfe(seed: number): ScatterPoint[] {
  const rng = mulberry32(seed);
  const points: { x: number; y: number }[] = [];

  for (let i = 0; i < 120; i++) {
    const x = rng() * 2000 + rng() * rng() * 3000;
    const y = rng() * 2500 + rng() * rng() * 4000;
    points.push({ x, y });
  }

  return hexbin(points, 120, 0, 6000, 30, 0, 7000, 40);
}

function generateFallbackDurationVsPnl(seed: number): ScatterPoint[] {
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
  const { trades } = useReportData(portfolioId, filterConfig);
  const tradeSignature = useMemo(
    () => trades.map((trade) => trade.id).join("|"),
    [trades],
  );

  return useQuery<ScatterAnalyticsResult, Error>({
    queryKey: [
      "scatter-analytics",
      portfolioId,
      filterConfig ? JSON.stringify(filterConfig) : null,
      tradeSignature,
    ],
    queryFn: async () => {
      if (!portfolioId) throw new Error("No portfolio selected");

      if (trades.length === 0) {
        return {
          maeMfe: [],
          durationVsPnl: [],
        };
      }

      let seedStr = portfolioId;
      if (filterConfig) {
        seedStr += JSON.stringify(filterConfig);
      }
      seedStr += tradeSignature;
      const seed = hashPortfolioId(seedStr);

      const maeMfeFromTrades = generateMaeMfeMock(trades, seed + 1);
      const durationVsPnlFromTrades = generateDurationVsPnlMock(trades);
      return {
        maeMfe:
          maeMfeFromTrades.length > 0
            ? maeMfeFromTrades
            : generateFallbackMaeMfe(seed + 1),
        durationVsPnl:
          durationVsPnlFromTrades.length > 0
            ? durationVsPnlFromTrades
            : generateFallbackDurationVsPnl(seed + 2),
      };
    },
    staleTime: 5 * 60 * 1000,
    enabled: !!portfolioId,
  });
}
