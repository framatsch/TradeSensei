/**
 * React Query hook for the drawdown time series.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import { getDrawdownCurveApiV1PortfoliosPortfolioIdMetricsDrawdownGet } from "@/lib/api/index";
import { client } from "@/lib/api/client.gen";
import type { DrawdownPoint, ResponseEnvelope } from "@/lib/types";

export function useDrawdown(portfolioId?: string) {
  return useQuery<DrawdownPoint[], Error>({
    queryKey: ["metrics", "drawdown", portfolioId],
    queryFn: async () => {
      if (portfolioId) {
        const { data, error } = await getDrawdownCurveApiV1PortfoliosPortfolioIdMetricsDrawdownGet({
          path: { portfolio_id: portfolioId },
        });
        if (error || !data) throw error;
        return (data as unknown as ResponseEnvelope<DrawdownPoint[]>).data;
      }
      const { data, error } = await client.get<ResponseEnvelope<DrawdownPoint[]>, unknown, false>({
        url: "/api/v1/metrics/drawdown",
      });
      if (error || !data) throw error;
      return data.data;
    },
    staleTime: 60 * 1000,
    enabled: !!portfolioId,
  });
}
