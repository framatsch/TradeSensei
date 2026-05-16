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
        if (error || !data) throw error ?? new Error("Request failed: no data returned");
        return (data as unknown as ResponseEnvelope<DrawdownPoint[]>).data;
      }
      const { data, error } = await client.get<ResponseEnvelope<DrawdownPoint[]>, unknown, false>({
        url: "/api/v1/metrics/drawdown",
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data;
    },
    staleTime: 60 * 1000,
    enabled: !!portfolioId,
  });
}
