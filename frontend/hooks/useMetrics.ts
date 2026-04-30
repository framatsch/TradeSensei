/**
 * React Query hook for metrics summary (includes equity curve + drawdown).
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import { getMetricsSummaryApiV1PortfoliosPortfolioIdMetricsSummaryGet } from "@/lib/api/index";
import { client } from "@/lib/api/client.gen";
import type { MetricsSummary, ResponseEnvelope } from "@/lib/types";

export function useMetrics(portfolioId?: string) {
  return useQuery<MetricsSummary, Error>({
    queryKey: ["metrics", "summary", portfolioId],
    queryFn: async () => {
      if (portfolioId) {
        const { data, error } = await getMetricsSummaryApiV1PortfoliosPortfolioIdMetricsSummaryGet({
          path: { portfolio_id: portfolioId },
        });
        if (error || !data) throw error ?? new Error("Request failed: no data returned");
        return (data as unknown as ResponseEnvelope<MetricsSummary>).data;
      }
      const { data, error } = await client.get<ResponseEnvelope<MetricsSummary>, unknown, false>({
        url: "/api/v1/metrics/summary",
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data;
    },
    staleTime: 60 * 1000,
    enabled: !!portfolioId,
  });
}
