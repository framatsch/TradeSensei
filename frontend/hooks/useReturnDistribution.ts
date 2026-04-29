/**
 * React Query hook for return distribution histogram data.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import { getReturnDistributionApiV1PortfoliosPortfolioIdTimeseriesReturnDistributionGet } from "@/lib/api/index";
import type { ReturnDistribution } from "@/lib/types";

export function useReturnDistribution(portfolioId?: string) {
  return useQuery<ReturnDistribution[], Error>({
    queryKey: ["metrics", "return-distribution", portfolioId],
    queryFn: async () => {
      const { data, error } = await getReturnDistributionApiV1PortfoliosPortfolioIdTimeseriesReturnDistributionGet({
        path: { portfolio_id: portfolioId! },
      });
      if (error || !data) throw error;
      return data.data as ReturnDistribution[];
    },
    staleTime: 5 * 60 * 1000,
    enabled: !!portfolioId,
  });
}
