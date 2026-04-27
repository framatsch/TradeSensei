/**
 * React Query hook for the drawdown time series.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import apiClient from "@/lib/api";
import type { DrawdownPoint, ResponseEnvelope } from "@/lib/types";

export function useDrawdown(portfolioId?: string) {
  return useQuery<DrawdownPoint[], Error>({
    queryKey: ["metrics", "drawdown", portfolioId],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (portfolioId) {
        params.append("portfolio_id", portfolioId);
      }
      const res = await apiClient.get<ResponseEnvelope<DrawdownPoint[]>>(
        `/api/v1/metrics/drawdown?${params.toString()}`
      );
      return res.data.data;
    },
    staleTime: 60 * 1000,
    enabled: !!portfolioId,
  });
}
