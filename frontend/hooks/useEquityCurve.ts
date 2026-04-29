/**
 * React Query hook for the equity curve time series.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import { getEquityCurveApiV1PortfoliosPortfolioIdMetricsEquityCurveGet } from "@/lib/api/index";
import { client } from "@/lib/api/client.gen";
import type { EquityCurvePoint, ResponseEnvelope } from "@/lib/types";

export function useEquityCurve(portfolioId?: string) {
  return useQuery<EquityCurvePoint[], Error>({
    queryKey: ["metrics", "equity-curve", portfolioId],
    queryFn: async () => {
      if (portfolioId) {
        const { data, error } = await getEquityCurveApiV1PortfoliosPortfolioIdMetricsEquityCurveGet({
          path: { portfolio_id: portfolioId },
        });
        if (error || !data) throw error;
        return (data as unknown as ResponseEnvelope<EquityCurvePoint[]>).data;
      }
      const { data, error } = await client.get<ResponseEnvelope<EquityCurvePoint[]>, unknown, false>({
        url: "/api/v1/metrics/equity-curve",
      });
      if (error || !data) throw error;
      return data.data;
    },
    staleTime: 60 * 1000,
    enabled: !!portfolioId,
  });
}
