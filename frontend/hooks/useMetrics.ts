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

/**
 * React Query hook for metrics summary (includes equity curve + drawdown).
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import { getMetricsSummaryApiV1PortfoliosPortfolioIdMetricsSummaryGet } from "@/lib/api/index";
import { client } from "@/lib/api/client.gen";
import type { MetricsSummary, ResponseEnvelope } from "@/lib/types";

export function useMetrics(portfolioId?: string) {
  return useQuery<MetricsSummary, Error>({
    queryKey: ["metrics", "summary", portfolioId],
    queryFn: async () => {
      if (portfolioId) {
        const { data, error } = await getMetricsSummaryApiV1PortfoliosPortfolioIdMetricsSummaryGet({
          path: { portfolio_id: portfolioId },
        });
        if (error || !data) throw error ?? new Error("Request failed: no data returned");
        return (data as unknown as ResponseEnvelope<MetricsSummary>).data;
      }
      const { data, error } = await client.get<ResponseEnvelope<MetricsSummary>, unknown, false>({
        url: "/api/v1/metrics/summary",
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data;
    },
    staleTime: 60 * 1000,
    enabled: !!portfolioId,
  });
}
