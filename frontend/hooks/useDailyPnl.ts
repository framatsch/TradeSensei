/**
 * React Query hook for daily PnL bar chart data (uses metrics summary equity
 * curve as the data source for now since a dedicated endpoint doesn't exist).
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import { getEquityCurveApiV1PortfoliosPortfolioIdMetricsEquityCurveGet } from "@/lib/api/index";
import { client } from "@/lib/api/client.gen";
import type { EquityCurvePoint, ResponseEnvelope } from "@/lib/types";

interface DailyPnlBar {
  date: string;
  pnl: number;
}

export function useDailyPnl(portfolioId?: string) {
  return useQuery<DailyPnlBar[], Error>({
    queryKey: ["metrics", "daily-pnl", portfolioId],
    queryFn: async () => {
      let points: EquityCurvePoint[];
      if (portfolioId) {
        const { data, error } = await getEquityCurveApiV1PortfoliosPortfolioIdMetricsEquityCurveGet({
          path: { portfolio_id: portfolioId },
        });
        if (error || !data) throw error ?? new Error("Request failed: no data returned");
        points = (data as unknown as ResponseEnvelope<EquityCurvePoint[]>).data;
      } else {
        const { data, error } = await client.get<ResponseEnvelope<EquityCurvePoint[]>, unknown, false>({
          url: "/api/v1/metrics/equity-curve",
        });
        if (error || !data) throw error ?? new Error("Request failed: no data returned");
        points = data.data;
      }
      // Aggregate per day from individual trade PnL values
      const byDate = new Map<string, number>();
      for (const point of points) {
        const date = point.timestamp.slice(0, 10);
        byDate.set(date, (byDate.get(date) ?? 0) + parseFloat(point.pnl));
      }
      return Array.from(byDate.entries())
        .map(([date, pnl]) => ({ date, pnl }))
        .sort((a, b) => a.date.localeCompare(b.date));
    },
    staleTime: 60 * 1000,
    enabled: !!portfolioId,
  });
}
