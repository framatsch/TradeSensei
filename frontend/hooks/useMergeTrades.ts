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
