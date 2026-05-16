/*
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

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
