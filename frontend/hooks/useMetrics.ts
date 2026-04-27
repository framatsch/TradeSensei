/**
 * React Query hook for metrics summary (includes equity curve + drawdown).
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import apiClient from "@/lib/api";
import type { MetricsSummary, ResponseEnvelope } from "@/lib/types";

export function useMetrics(portfolioId?: string) {
  return useQuery<MetricsSummary, Error>({
    queryKey: ["metrics", "summary", portfolioId],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (portfolioId) {
        params.append("portfolio_id", portfolioId);
      }
      const res = await apiClient.get<ResponseEnvelope<MetricsSummary>>(
        `/api/v1/metrics/summary?${params.toString()}`
      );
      return res.data.data;
    },
    staleTime: 60 * 1000,
    enabled: !!portfolioId,
  });
}
