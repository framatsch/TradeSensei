"use client";

import { useQuery } from "@tanstack/react-query";
import { getMetadataCorrelationApiV1PortfoliosPortfolioIdAnalyticsMetadataCorrelationGet } from "@/lib/api/index";
import type {
  GetMetadataCorrelationApiV1PortfoliosPortfolioIdAnalyticsMetadataCorrelationGetData,
  MetadataCorrelationResponse,
} from "@/lib/api/types.gen";

type MetadataCorrelationParams = Omit<
  GetMetadataCorrelationApiV1PortfoliosPortfolioIdAnalyticsMetadataCorrelationGetData["query"],
  "portfolio_id"
> & {
  portfolioId: string;
};

const QUERY_KEY = ["metadata-correlation"] as const;

export function useMetadataCorrelation(params: MetadataCorrelationParams) {
  const { portfolioId, ...query } = params;

  return useQuery<MetadataCorrelationResponse, Error>({
    queryKey: [...QUERY_KEY, portfolioId, query],
    queryFn: async () => {
      const { data, error } =
        await getMetadataCorrelationApiV1PortfoliosPortfolioIdAnalyticsMetadataCorrelationGet({
          path: { portfolio_id: portfolioId },
          query: query as GetMetadataCorrelationApiV1PortfoliosPortfolioIdAnalyticsMetadataCorrelationGetData["query"],
        });

      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data as MetadataCorrelationResponse;
    },
    enabled: !!(query.x_axis_id && query.y_axis_id),
    staleTime: 60_000, // 1 minute
  });
}
