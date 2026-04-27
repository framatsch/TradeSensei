/**
 * React Query hook for the equity curve time series.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import apiClient from "@/lib/api";
import type { EquityCurvePoint, ResponseEnvelope } from "@/lib/types";

export function useEquityCurve(portfolioId?: string) {
  return useQuery<EquityCurvePoint[], Error>({
    queryKey: ["metrics", "equity-curve", portfolioId],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (portfolioId) {
        params.append("portfolio_id", portfolioId);
      }
      const res = await apiClient.get<ResponseEnvelope<EquityCurvePoint[]>>(
        `/api/v1/metrics/equity-curve?${params.toString()}`
      );
      return res.data.data;
    },
    staleTime: 60 * 1000,
    enabled: !!portfolioId,
  });
}
