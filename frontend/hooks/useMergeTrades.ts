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
 * React Query hook for merging multiple trades into one.
 */

"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { mergeTradesApiV1PortfoliosPortfolioIdTradesMergePost } from "@/lib/api/index";
import { usePortfolioStore } from "@/stores/portfolioStore";
import type { MergeTradesRequest, Trade } from "@/lib/types";

/** Merge two or more trades into a single surviving trade. */
export function useMergeTrades() {
  const qc = useQueryClient();
  const portfolioId = usePortfolioStore((state) => state.activePortfolioId);
  return useMutation<Trade, Error, MergeTradesRequest>({
    mutationFn: async (payload) => {
      const { data, error } = await mergeTradesApiV1PortfoliosPortfolioIdTradesMergePost({
        path: { portfolio_id: portfolioId! },
        body: payload,
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return (data as any).data as Trade;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["trades"] });
      void qc.invalidateQueries({ queryKey: ["metrics"] });
    },
  });
}
