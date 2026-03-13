/**
 * React Query hook for metrics summary (includes equity curve + drawdown).
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import apiClient from "@/lib/api";
import type { MetricsSummary, ResponseEnvelope } from "@/lib/types";

export function useMetrics() {
  return useQuery<MetricsSummary, Error>({
    queryKey: ["metrics", "summary"],
    queryFn: async () => {
      const res = await apiClient.get<ResponseEnvelope<MetricsSummary>>(
        "/api/v1/metrics/summary"
      );
      return res.data.data;
    },
    staleTime: 60 * 1000,
  });
}
