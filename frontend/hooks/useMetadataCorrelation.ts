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
import { getMetadataCorrelationApiV1PortfoliosPortfolioIdAnalyticsCorrelationsMetadataPost } from "@/lib/api/index";
import type {
  MetadataCorrelationResponse,
  DashboardFilterConfig,
} from "@/lib/api/types.gen";

type MetadataCorrelationParams = {
  portfolioId: string;
  x_axis_type: any;
  x_axis_id: string;
  y_axis_type: any;
  y_axis_id: string;
  base_asset?: string;
  filter_config?: DashboardFilterConfig;
  view_id?: string;
};

const QUERY_KEY = ["metadata-correlation"] as const;

export function useMetadataCorrelation(params: MetadataCorrelationParams) {
  const { portfolioId, ...query } = params;

  return useQuery<MetadataCorrelationResponse, Error>({
    queryKey: [...QUERY_KEY, portfolioId, query],
    queryFn: async () => {
      const body: any = {
        x_axis_type: query.x_axis_type,
        x_axis_id: query.x_axis_id,
        y_axis_type: query.y_axis_type,
        y_axis_id: query.y_axis_id,
        base_asset: query.base_asset,
      };

      if (query.view_id) {
        body.view_id = query.view_id;
      } else {
        body.filter_config = query.filter_config || {};
      }

      const { data, error } =
        await getMetadataCorrelationApiV1PortfoliosPortfolioIdAnalyticsCorrelationsMetadataPost({
          path: { portfolio_id: portfolioId },
          body: body as any,
        });

      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data as MetadataCorrelationResponse;
    },
    enabled: !!(query.x_axis_id && query.y_axis_id),
    staleTime: 60_000, // 1 minute
  });
}
