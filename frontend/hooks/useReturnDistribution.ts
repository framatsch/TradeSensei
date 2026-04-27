/**
 * React Query hook for return distribution histogram data.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import apiClient from "@/lib/api";
import type { ReturnDistribution, ResponseEnvelope } from "@/lib/types";

export function useReturnDistribution(portfolioId?: string) {
  return useQuery<ReturnDistribution[], Error>({
    queryKey: ["metrics", "return-distribution", portfolioId],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (portfolioId) {
        params.append("portfolio_id", portfolioId);
      }
      const res = await apiClient.get<ResponseEnvelope<ReturnDistribution[]>>(
        `/api/v1/timeseries/return-distribution?${params.toString()}`
      );
      return res.data.data;
    },
    staleTime: 5 * 60 * 1000,
    enabled: !!portfolioId,
  });
}
